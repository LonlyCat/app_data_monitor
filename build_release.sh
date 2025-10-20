#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "用法: ./build_release.sh <version> [--push] [--image <repo/image>] [--platform <p1,p2>]"
  echo "示例: ./build_release.sh 0.0.3 --push --platform linux/amd64,linux/arm64"
}

if [[ ${1:-} == "" ]]; then
  usage; exit 1
fi

VERSION="$1"; shift || true
PUSH=0
IMAGE="docker.io/lbs19312/app-data-monitor:${VERSION}"
PLATFORM="linux/amd64,linux/arm64"

while [[ ${1:-} != "" ]]; do
  case "$1" in
    --push) PUSH=1; shift ;;
    --image) IMAGE="$2"; shift 2 ;;
    --platform) PLATFORM="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知参数: $1"; usage; exit 1 ;;
  esac
done

echo "📦 构建镜像: ${IMAGE}"
if docker buildx version >/dev/null 2>&1; then
  if [[ $PUSH -eq 1 ]]; then
    docker buildx build --platform "${PLATFORM}" -t "${IMAGE}" --push .
  else
    # --load 仅支持单平台加载到本地
    SINGLE_PLATFORM="${PLATFORM%%,*}"
    echo "ℹ️ 未指定 --push，默认仅构建并加载单平台: ${SINGLE_PLATFORM}"
    docker buildx build --platform "${SINGLE_PLATFORM}" -t "${IMAGE}" --load .
  fi
else
  echo "⚠️ 未检测到 buildx，回退到本地 docker build（不支持多架构）"
  if [[ "$PLATFORM" != *","* ]]; then
    DOCKER_DEFAULT_PLATFORM="$PLATFORM" docker build -t "${IMAGE}" .
  else
    docker build -t "${IMAGE}" .
  fi
  if [[ $PUSH -eq 1 ]]; then
    docker push "${IMAGE}"
  fi
fi

echo "✅ 完成。可更新 .env.release 中的 WEB_IMAGE=${IMAGE} 或运行: ./start_release.sh --image ${IMAGE}"
