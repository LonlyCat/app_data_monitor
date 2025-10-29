#!/usr/bin/env bash

# 一键安装 scheduler_tick 的定时触发（cron 或 systemd）
#
# 用法示例：
#   ./setup_scheduler_tick.sh            # 为当前用户安装 cron，每分钟执行一次
#   ./setup_scheduler_tick.sh --with-reboot   # 额外添加 @reboot，确保重启后自动启动 compose 堆栈
#   ./setup_scheduler_tick.sh --remove        # 卸载（移除 cron / systemd）
#   ./setup_scheduler_tick.sh --systemd       # 使用 systemd timer 安装（需 root）
#
# 可选参数：
#   --project-dir <PATH>     项目根目录（默认：脚本所在目录）
#   --compose-file <FILE>    compose 文件（默认：docker-compose.release.yml）
#   --project-name <NAME>    compose 项目名（默认：项目目录名）
#   --interval <CRON>        cron 表达式（默认："* * * * *"）
#   --delay <SEC>            每次执行前 sleep 秒数（默认：10，帮助等待容器就绪）
#   --with-reboot            添加 @reboot 启动 compose 堆栈
#   --systemd                使用 systemd timer （root）安装，替代 cron
#   --remove                 卸载（移除 cron / systemd 定时与开机项）

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_DIR="$SCRIPT_DIR"
COMPOSE_FILE="docker-compose.release.yml"
PROJECT_NAME=$(basename "$PROJECT_DIR")
CRON_EXPR="* * * * *"
DELAY_SEC=10
USE_SYSTEMD=false
WITH_REBOOT=false
DO_REMOVE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-dir) PROJECT_DIR="$2"; shift 2 ;;
    --compose-file) COMPOSE_FILE="$2"; shift 2 ;;
    --project-name) PROJECT_NAME="$2"; shift 2 ;;
    --interval) CRON_EXPR="$2"; shift 2 ;;
    --delay) DELAY_SEC="$2"; shift 2 ;;
    --systemd) USE_SYSTEMD=true; shift 1 ;;
    --with-reboot) WITH_REBOOT=true; shift 1 ;;
    --remove) DO_REMOVE=true; shift 1 ;;
    -h|--help)
      sed -n '1,80p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

# 解析 docker compose 命令
resolve_compose_cmd() {
  local docker_bin dc
  docker_bin=$(command -v docker || true)
  if [[ -n "$docker_bin" ]] && "$docker_bin" compose version &>/dev/null; then
    echo "$docker_bin compose"
    return 0
  fi
  dc=$(command -v docker-compose || true)
  if [[ -n "$dc" ]]; then
    echo "$dc"
    return 0
  fi
  echo ""; return 1
}

DC=$(resolve_compose_cmd || true)
if [[ -z "$DC" ]]; then
  echo "❌ 未检测到 docker compose，请先安装 Docker Compose (v2/v1 均可)"
  exit 1
fi

mkdir -p "$PROJECT_DIR/logs"
LOG_FILE="$PROJECT_DIR/logs/scheduler-cron.log"
touch "$LOG_FILE"

CRON_TAG="# app_data_monitor:scheduler_tick"
CRON_REBOOT_TAG="# app_data_monitor:reboot_compose"

CRON_CMD="cd $PROJECT_DIR && sleep $DELAY_SEC; $DC -f $COMPOSE_FILE -p $PROJECT_NAME exec -T web python manage.py scheduler_tick >> $LOG_FILE 2>&1"
REBOOT_CMD="cd $PROJECT_DIR && $DC -f $COMPOSE_FILE -p $PROJECT_NAME up -d >> $PROJECT_DIR/logs/compose-reboot.log 2>&1"

install_cron() {
  echo "🛠️ 写入用户 crontab ..."
  local tmp
  tmp=$(mktemp)
  crontab -l 2>/dev/null | grep -v "$CRON_TAG" | grep -v "$CRON_REBOOT_TAG" > "$tmp" || true
  echo "$CRON_TAG" >> "$tmp"
  echo "$CRON_EXPR $CRON_CMD" >> "$tmp"
  if $WITH_REBOOT; then
    echo "$CRON_REBOOT_TAG" >> "$tmp"
    echo "@reboot $REBOOT_CMD" >> "$tmp"
  fi
  crontab "$tmp"
  rm -f "$tmp"
  echo "✅ 已安装 cron：$CRON_EXPR"
  echo "   任务：$CRON_CMD"
  $WITH_REBOOT && echo "   开机：@reboot $REBOOT_CMD" || true
}

uninstall_cron() {
  echo "🧹 移除用户 crontab 项 ..."
  local tmp
  tmp=$(mktemp)
  crontab -l 2>/dev/null | grep -v "$CRON_TAG" | grep -v "$CRON_REBOOT_TAG" > "$tmp" || true
  crontab "$tmp" || true
  rm -f "$tmp"
  echo "✅ 已移除 cron 项"
}

SYSTEMD_SERVICE="/etc/systemd/system/app-monitor-scheduler-tick.service"
SYSTEMD_TIMER="/etc/systemd/system/app-monitor-scheduler-tick.timer"

install_systemd() {
  if [[ $EUID -ne 0 ]]; then
    echo "❌ --systemd 需要 root 权限（请使用 sudo）"; exit 1
  fi
  local docker_bin
  docker_bin=$(command -v docker || true)
  if [[ -z "$docker_bin" ]]; then
    echo "❌ 未检测到 docker，可用性未知"; exit 1
  fi

  echo "🛠️ 安装 systemd service 与 timer ..."

  cat > "$SYSTEMD_SERVICE" <<EOF
[Unit]
Description=App Monitor Scheduler Tick (oneshot)
Wants=docker.service
After=docker.service

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
ExecStart=$DC -f $COMPOSE_FILE -p $PROJECT_NAME exec -T web python manage.py scheduler_tick
StandardOutput=append:$LOG_FILE
StandardError=append:$LOG_FILE
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

  cat > "$SYSTEMD_TIMER" <<EOF
[Unit]
Description=Run App Monitor Scheduler Tick every minute

[Timer]
OnCalendar=*-*-* *:*:00
AccuracySec=1s
Unit=$(basename "$SYSTEMD_SERVICE")
Persistent=true

[Install]
WantedBy=timers.target
EOF

  systemctl daemon-reload
  systemctl enable --now $(basename "$SYSTEMD_TIMER")
  echo "✅ 已启用 systemd timer：$(basename "$SYSTEMD_TIMER")"

  if $WITH_REBOOT; then
    # 以 systemd 方式确保 compose 栈随开机启动（若你已有独立的 compose 管理，不必启用）
    # 这里推荐在其他地方保证 compose up -d，我们不强行创建另一个服务，避免冲突。
    echo "ℹ️ 如需确保 compose 堆栈随开机启动，请保证相应的 systemd/rc.local 规则或 Docker 自启动策略已配置。"
  fi
}

uninstall_systemd() {
  if [[ $EUID -ne 0 ]]; then
    echo "❌ --remove --systemd 需要 root 权限（请使用 sudo）"; exit 1
  fi
  echo "🧹 移除 systemd timer/service ..."
  systemctl disable --now $(basename "$SYSTEMD_TIMER") || true
  rm -f "$SYSTEMD_TIMER" || true
  rm -f "$SYSTEMD_SERVICE" || true
  systemctl daemon-reload
  echo "✅ 已移除 systemd timer/service"
}

echo "📌 配置参数："
echo "  PROJECT_DIR = $PROJECT_DIR"
echo "  COMPOSE_FILE = $COMPOSE_FILE"
echo "  PROJECT_NAME = $PROJECT_NAME"
echo "  使用 = $($USE_SYSTEMD && echo systemd || echo cron)"

if $DO_REMOVE; then
  if $USE_SYSTEMD; then
    uninstall_systemd
  else
    uninstall_cron
  fi
  exit 0
fi

if $USE_SYSTEMD; then
  install_systemd
else
  install_cron
fi

echo "🎉 完成。日志：$LOG_FILE"

