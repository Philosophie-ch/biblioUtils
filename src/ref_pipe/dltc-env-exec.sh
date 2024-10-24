#!/usr/bin/env bash

function help_msg() {
cat << EOF
Usage: ./dltc-env-start.sh [OPTIONS]

OPTIONS:
    -h, --help      Show this message

Starts a dltc-env container. This script pulls the latest dltc-env image from Docker Hub and then uses docker compose to start the container.

EOF
}

case "$1" in
    "-h" | "--help")
        help_msg
        exit 0
        ;;
esac


############
# SETUP
############

_LOG_DIR="${PWD}/logs"
_LOG_FILE="${_LOG_DIR}/dltc-env-start.log"
mkdir -p "${_LOG_DIR}"

cat << EOF > "${_LOG_FILE}"
DLTC-ENV-START LOG
--------------------------------

0. Setup

EOF

# Check if docker is installed
if ! [ -x "$(command -v docker)" ]; then
  printf 'Error: docker is not installed.\nPlease install it and then retry.' | tee -a "${_LOG_FILE}"
  exit 1
fi

# Read from .env file if it exists, else exit with error
set -a
if [ -f ".env" ]; then
    . .env
else
    printf "No .env file found.\nPlease copy the .env.template file with the name ".env" and fill in the required variables.\n" | tee -a "${_LOG_FILE}"
    exit 1
fi
set +a

required_env_vars=( "ARCH" "DLTC_WORKHOUSE_DIRECTORY" "DOCKERHUB_TOKEN" )

# Check if required environment variables are set
for var_name in "${required_env_vars[@]}"; do
    if [ -z "${!var_name}" ]; then
        no_env_var_msg "${var_name}" | tee -a "${_LOG_FILE}"
        exit 1
    fi
done

# Check if ARCH is set to "arm64" or "amd64"
if [ "${ARCH}" != "arm64" ] && [ "${ARCH}" != "amd64" ]; then
    cat << EOF | tee -a "${_LOG_FILE}"
Error: ARCH must be set to "arm64" or "amd64".
Please set it to the correct value for your machine in the .env file:

For Windows, Linux, and Mac (Intel) machines, set ARCH=amd64
For Mac (Apple Silicon: M1, M2, M3) machines, set ARCH=arm64

EOF
    exit 1
fi

# Check if DLTC_WORKHOUSE_DIRECTORY exists
if [ ! -d "${DLTC_WORKHOUSE_DIRECTORY}" ]; then
    printf 'Error: the folder '${DLTC_WORKHOUSE_DIRECTORY}' set for DLTC_WORKHOUSE_DIRECTORY does not exist.\nPlease put the path to the shared dltc-workhouse folder in Dropbox.\n' | tee -a "${_LOG_FILE}"
    exit 1
fi

DOCKERHUB_USERNAME=philosophiech

DOCKER_IMAGE_NAME_TAG="${DOCKERHUB_USERNAME}/dltc-env:latest-${ARCH}"

printf "All dependencies found, and environment variables are all correctly set.\n\n" >> "${_LOG_FILE}"


############
# MAIN
############

echo "Starting the container, please wait..."

# 1. Login to dockerhub
echo "...logging in to Docker Hub..."

printf "1. Log in to Docker Hub\n\n" >> "${_LOG_FILE}"

echo "${DOCKERHUB_TOKEN}" | docker login -u "${DOCKERHUB_USERNAME}" --password-stdin >> "${_LOG_FILE}" 2>&1
_LOGIN_STATUS=$?

if [ ${_LOGIN_STATUS} -ne 0 ]; then
  printf "Error: Could not log in to Docker Hub.\nPlease check the log file at ${_LOG_FILE} for more information.\n"
  exit 1
fi

printf "Logged in to Docker Hub as ${DOCKERHUB_USERNAME}\n\n" >> "${_LOG_FILE}"


# 2. Pull latest dltc-env image
echo "...pulling latest dltc-env image for ${ARCH}..."

printf "2. Pull latest dltc-env image for ${ARCH}\n\n" >> "${_LOG_FILE}"

docker pull "${DOCKER_IMAGE_NAME_TAG}" >> "${_LOG_FILE}" 2>&1
_PULL_STATUS=$?
echo "" >> "${_LOG_FILE}"

if [ ${_PULL_STATUS} -ne 0 ]; then
  printf "Error: Could not pull latest dltc-env image for ${ARCH}.\nPlease check the log file at ${_LOG_FILE} for more information.\n"
  exit 1
fi

docker inspect --type=image "${DOCKER_IMAGE_NAME_TAG}" > /dev/null 2>&1
_INSPECT_STATUS=$?

if [ ${_INSPECT_STATUS} -ne 0 ]; then
  printf "Error: Could not find the dltc-env image locally.\nPlease check the log file at ${_LOG_FILE} for more information.\n"
  exit 1
fi
printf "${DOCKER_IMAGE_NAME_TAG} image found locally.\n\n" >> "${_LOG_FILE}"

docker logout >> "${_LOG_FILE}" 2>&1
echo "" >> "${_LOG_FILE}"


# 3. Start dltc-env container
# Check which of these two commands is available: docker compose or docker-compose
echo "...starting the container..."

printf "3. Start the container\n\n" >> "${_LOG_FILE}"

if [ -x "$(command -v docker-compose)" ]; then
    docker-compose -f docker-compose.yml down >> "${_LOG_FILE}" 2>&1 && \
    docker-compose -f docker-compose.yml up -d >> "${_LOG_FILE}" 2>&1
    _COMPOSE_STATUS=$?
else
    docker compose -f docker-compose.yml down >> "${_LOG_FILE}" 2>&1 && \
    docker compose -f docker-compose.yml up -d >> "${_LOG_FILE}" 2>&1
    _COMPOSE_STATUS=$?
fi
echo "" >> "${_LOG_FILE}"

if [ ${_COMPOSE_STATUS} -ne 0 ]; then
    printf "Error: Could not start dltc-env container.\nPlease check the log file at ${_LOG_FILE} for more information.\n"
    exit 1
fi

printf "\nResult: Success!\n" >> "${_LOG_FILE}"

echo "...container started successfully!"
