#!/usr/bin/env bash

# App数据监控系统 - 无代码部署（基于预构建镜像）
# 优化点：
# - 统一 docker compose(v1/v2) 调用
# - 支持从 .env.release 读取 WEB_IMAGE（可被 --image 覆盖）
# - 参数更灵活：--compose-file/--project/--no-pull/--no-wait/--health-url
# - 依赖容器 entrypoint 进行迁移与静态收集（不再重复执行）
# - 可选等待健康检查接口就绪

set -euo pipefail

# -------------------------------
# 基础输出函数
# -------------------------------
log()  { echo "📘 $*"; }
ok()   { echo "✅ $*"; }
warn() { echo "⚠️  $*"; }
err()  { echo "❌ $*" 1>&2; }

echo "🚀 启动App数据监控系统（无代码部署 / Release 镜像）..."

usage() {
  cat <<'USAGE'
用法: ./start_release.sh [选项]

常用选项：
  --image <IMAGE>          指定预构建镜像（优先级最高）
  --compose-file <PATH>    指定 compose 文件（默认: docker-compose.release.yml）
  --project <NAME>         指定 compose 项目名（默认: 当前目录名）
  --no-pull                启动前不执行 docker pull（默认会尝试）
  --no-wait                启动后不等待健康检查就绪
  --health-url <URL>       健康检查URL（默认: http://localhost:8000/api/health/）
  -h, --help               显示帮助

说明：
  - 该脚本使用 docker-compose.release.yml，通过 WEB_IMAGE 指定预构建镜像
  - 服务端无需拉取源代码，仅需该 compose 文件和 .env.release 即可
  - 容器入口脚本会执行迁移、收集静态文件，并可按 DJANGO_SUPERUSER_* 自动创建管理员
USAGE
}

# -------------------------------
# 解析参数
# -------------------------------
IMAGE_ARG="${WEB_IMAGE:-}"
COMPOSE_FILE_DEFAULT="docker-compose.release.yml"
COMPOSE_FILE="$COMPOSE_FILE_DEFAULT"
PROJECT_NAME="$(basename "$PWD")"
PULL_IMAGE=1
WAIT_HEALTH=1
HEALTH_URL="http://localhost:8000/api/health/"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --image)
      IMAGE_ARG="$2"; shift 2 ;;
    --compose-file)
      COMPOSE_FILE="$2"; shift 2 ;;
    --project)
      PROJECT_NAME="$2"; shift 2 ;;
    --no-pull)
      PULL_IMAGE=0; shift ;;
    --no-wait)
      WAIT_HEALTH=0; shift ;;
    --health-url)
      HEALTH_URL="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      err "未知参数: $1"; usage; exit 1 ;;
  esac
done

# -------------------------------
# 前置检查
# -------------------------------
if ! command -v docker &>/dev/null; then
  err "未检测到 docker，请先安装 docker"; exit 1
fi

# 选择 compose 命令
if docker compose version &>/dev/null; then
  DC=(docker compose)
elif command -v docker-compose &>/dev/null; then
  DC=(docker-compose)
else
  err "未检测到 docker compose，请先安装 docker compose"; exit 1
fi

if [ ! -f .env.release ]; then
  warn "未检测到 .env.release，基于模板创建..."
  cp .env.release.example .env.release
  warn "请编辑 .env.release 填写正确的 SECRET_KEY、ALLOWED_HOSTS、ENCRYPTION_KEY 等后再次运行"
  exit 1
fi

# 将 .env.release 中的变量导入当前环境（用于模板替换，如 WEB_IMAGE）
# 仅当文件存在且安全可读时执行；注意：仅影响 compose 模板替换，不会直接注入容器环境
set -a
# shellcheck disable=SC1091
. ./.env.release
set +a

# 若未通过参数/环境提供镜像，尝试使用 .env.release 中的 WEB_IMAGE
if [[ -z "${IMAGE_ARG:-}" && -n "${WEB_IMAGE:-}" ]]; then
  IMAGE_ARG="$WEB_IMAGE"
fi

if [[ -z "${IMAGE_ARG:-}" ]]; then
  err "必须通过 --image 或环境变量 WEB_IMAGE 指定镜像，例如: docker.io/yourrepo/app-data-monitor:1.0.0"
  exit 1
fi

export WEB_IMAGE="$IMAGE_ARG"
log "使用镜像: $WEB_IMAGE"

# 额外的基本校验（给出友好提示，不阻断执行）
if [[ "${SECRET_KEY:-}" == "django-insecure-development-key-only" ]]; then
  warn "检测到默认 SECRET_KEY，建议在 .env.release 中更换为安全随机值"
fi
if [[ "${ENCRYPTION_KEY:-CHANGE_ME}" == "CHANGE_ME" ]]; then
  warn "检测到默认 ENCRYPTION_KEY=CHANGE_ME，建议生成后更新（见 .env.release.example 注释）"
fi

# -------------------------------
# 启动流程
# -------------------------------
log "清理旧容器(如有)..."
"${DC[@]}" -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down --remove-orphans || true

if [[ $PULL_IMAGE -eq 1 ]]; then
  log "拉取镜像..."
  docker pull "$WEB_IMAGE" || warn "拉取镜像失败，可能离线或无权限，将尝试直接启动本地缓存镜像"
else
  log "跳过拉取镜像 (--no-pull)"
fi

log "启动服务..."
"${DC[@]}" -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d

# 由容器 entrypoint 负责等待数据库、迁移与收集静态

# 可选：等待健康检查
if [[ $WAIT_HEALTH -eq 1 ]]; then
  if command -v curl >/dev/null 2>&1; then
    log "等待服务健康检查就绪: $HEALTH_URL"
    ATTEMPTS=90
    SLEEP=1
    for ((i=1; i<=ATTEMPTS; i++)); do
      if curl -fsS "$HEALTH_URL" | grep -qi '"status"\s*:\s*"ok"'; then
        ok "健康检查通过 (第 $i 次检测)"
        HEALTH_OK=1
        break
      fi
      sleep "$SLEEP"
    done
    if [[ ${HEALTH_OK:-0} -ne 1 ]]; then
      warn "在 ${ATTEMPTS}s 内未检测到健康检查就绪，请稍后再试或查看日志"
    fi
  else
    warn "系统未安装 curl，跳过健康检查等待"
  fi
else
  log "已禁用健康检查等待 (--no-wait)"
fi

echo ""
ok "系统启动完成！"
echo ""
echo "📋 访问信息："
echo "   管理后台: http://localhost:8000/admin"
echo "   API健康检查: http://localhost:8000/api/health/"
if [[ -n "${ALLOWED_HOSTS:-}" ]]; then
  echo "   当前 ALLOWED_HOSTS: ${ALLOWED_HOSTS}"
  echo "   如通过内网IP访问，请确保该IP已包含在 ALLOWED_HOSTS 中（逗号分隔），或在 .env.release 中设置 ALLOWED_HOSTS=* 进行临时放行（仅限内网/测试）。"
else
  echo "   提示：未在 .env.release 中检测到 ALLOWED_HOSTS，默认仅允许 localhost,127.0.0.1"
fi
echo ""
echo "🔧 常用命令："
echo "   查看日志: ${DC[*]} -f $COMPOSE_FILE -p $PROJECT_NAME logs -f web"
echo "   停止服务: ${DC[*]} -f $COMPOSE_FILE -p $PROJECT_NAME down"
echo ""
echo "ℹ️ 提示: 可在 .env.release 中配置 DJANGO_SUPERUSER_* 变量实现自动创建管理员"
