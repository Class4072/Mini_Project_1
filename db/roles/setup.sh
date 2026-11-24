#!/usr/bin/env bash
# =============================================================
# setup.sh — 서비스 DB 계정과 권한을 한 번에 준비한다 (db/roles 00~04를 순서대로 실행)
#
# DB 관리자(슈퍼유저)가 자기 컴퓨터의 터미널에서 실행한다. 몇 번 실행해도 결과가 같다.
#
#   PGHOST=DB서버주소 ADMIN_USER=관리자계정 ./db/roles/setup.sh
#
# 설정 (환경변수)
#   PGHOST      DB 서버 주소 (필수)
#   ADMIN_USER  슈퍼유저 계정 (필수)
#   PGPORT      포트 (기본 5432)
#   ADMIN_DB    관리자가 처음 접속할 DB (기본 postgres)
#   TARGET_DB   계정·권한을 적용할 DB (기본 tour_db). 없으면 새로 만든다. 다른 DB는 건드리지 않는다.
#
# 순서
#   1. 접속하고 슈퍼유저인지 확인
#   2. TARGET_DB가 없으면 만든다
#   3. 00 점검 → 4. 01 계정 생성 → 5. 계정 비밀번호 입력 → 6. 02 PUBLIC 권한 회수
#   → 7. 03 테이블 권한 → 8. 04 검증
#
# 비밀번호는 파일에 남지 않는다.
#   - 관리자 비밀번호: 처음에 한 번 묻고, 이 스크립트가 실행하는 psql에만 넘긴다.
#   - 서비스 계정 비밀번호: psql \password 로 입력한다 (화면에 안 보이고, 암호화된 값만 서버로 감).
# 터미널이 아닌 곳에서 실행하면 비밀번호 입력은 건너뛰고 상태만 알려준다.
# =============================================================
set -euo pipefail

ROLES_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_ROLES="tp_owner tp_batch tp_ai tp_backend"

: "${PGHOST:?PGHOST(DB 서버 주소)를 지정하세요. 예: PGHOST=DB서버주소}"
: "${ADMIN_USER:?ADMIN_USER(슈퍼유저 계정)를 지정하세요. 예: ADMIN_USER=관리자계정}"
export PGHOST
export PGPORT="${PGPORT:-5432}"
export PGUSER="$ADMIN_USER"
ADMIN_DB="${ADMIN_DB:-postgres}"
TARGET_DB="${TARGET_DB:-tour_db}"

if ! [[ "$TARGET_DB" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    echo "TARGET_DB에는 영문·숫자·밑줄만 쓸 수 있습니다: $TARGET_DB" >&2
    exit 1
fi
if ! command -v psql >/dev/null 2>&1; then
    echo "psql이 없습니다. macOS: brew install libpq && export PATH=\"/opt/homebrew/opt/libpq/bin:\$PATH\"" >&2
    exit 1
fi

step() { printf '\n==== %s\n' "$1"; }
is_tty() { [ -t 0 ] && [ -t 1 ]; }
psql_admin() { psql -X -q -v ON_ERROR_STOP=1 -d "$ADMIN_DB" "$@"; }
psql_target() { psql -X -v ON_ERROR_STOP=1 -d "$TARGET_DB" "$@"; }
# 01~03을 실행한다. 각 파일 끝의 "완료. 다음 …" 안내는 이 스크립트가 이어서 하므로 숨긴다.
run_step_sql() { psql_target -q "$@" | sed '/^완료\. 다음/,$d'; }

# 관리자 비밀번호는 한 번만 묻는다 (.pgpass를 쓰거나 비밀번호가 필요 없으면 엔터)
if [ -z "${PGPASSWORD:-}" ] && is_tty; then
    read -rsp "$ADMIN_USER 비밀번호: " admin_password
    echo
    if [ -n "$admin_password" ]; then
        export PGPASSWORD="$admin_password"
    fi
    unset admin_password
fi

step "1. 접속 확인 ($ADMIN_USER@$PGHOST:$PGPORT)"
is_super=$(psql_admin -At -c "SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
if [ "$is_super" != "t" ]; then
    echo "$ADMIN_USER 는 슈퍼유저가 아닙니다. 계정 생성은 슈퍼유저로 실행해야 합니다." >&2
    exit 1
fi
echo "접속됨, 슈퍼유저 확인"

step "2. 데이터베이스 $TARGET_DB"
created_now=0
db_exists=$(psql_admin -At -v db="$TARGET_DB" <<'SQL'
SELECT count(*) FROM pg_database WHERE datname = :'db';
SQL
)
if [ "$db_exists" = "0" ]; then
    psql_admin -v db="$TARGET_DB" <<'SQL'
CREATE DATABASE :"db";
SQL
    created_now=1
    echo "새로 만들었습니다. 다른 DB는 건드리지 않았습니다."
else
    echo "이미 있습니다"
fi

step "3. 실행 전 점검 (00_precheck.sql)"
psql_target -f "$ROLES_DIR/00_precheck.sql"

step "4. 서비스 계정 만들기 (01_create_roles.sql)"
run_step_sql -f "$ROLES_DIR/01_create_roles.sql"

step "5. 서비스 계정 비밀번호"
for role in $SERVICE_ROLES; do
    has_password=$(psql_target -At -c "SELECT rolpassword IS NOT NULL FROM pg_authid WHERE rolname = '$role'")
    if ! is_tty; then
        if [ "$has_password" = "t" ]; then
            echo "$role: 비밀번호 있음"
        else
            echo "$role: 비밀번호 없음 → 터미널에서 다시 실행하거나 psql -d $TARGET_DB -c '\\password $role'"
        fi
        continue
    fi
    if [ "$has_password" = "t" ]; then
        read -rp "$role: 이미 비밀번호가 있습니다. 새로 정할까요? [y/N] " answer
        case "$answer" in
            [yY]*) ;;
            *) continue ;;
        esac
    fi
    echo "$role 비밀번호를 두 번 입력하세요"
    psql_target -c "\\password $role"
done

step "6. 모든 계정에 열린 기본 권한(PUBLIC) 회수 (02_lockdown_public.sql)"
public_open=$(psql_target -At -c \
    "SELECT has_database_privilege('public', current_database(), 'CONNECT') OR has_schema_privilege('public', 'public', 'USAGE')")
if [ "$public_open" = "f" ]; then
    echo "이미 회수돼 있어 건너뜁니다"
elif [ "$created_now" = "1" ]; then
    # 방금 만든 DB라 기존 계정이 이 DB를 쓸 일이 없다
    run_step_sql -v allow_block=1 -f "$ROLES_DIR/02_lockdown_public.sql"
else
    # 기존 DB: PUBLIC 권한으로만 쓰던 계정이 있으면 02가 아무것도 바꾸지 않고 멈춘다
    run_step_sql -f "$ROLES_DIR/02_lockdown_public.sql"
fi

step "7. 테이블 권한 (03_grant_tables.sql)"
run_step_sql -f "$ROLES_DIR/03_grant_tables.sql"

step "8. 검증 (04_verify.sql) — [2], [3], [5]가 비어 있어야 정상"
psql_target -f "$ROLES_DIR/04_verify.sql"

cat <<EOF

완료. 다음 순서:
  1) 테이블 만들기: 백엔드를 $TARGET_DB 에 한 번 실행하면 Flyway가 tp_owner로 db/migration을 적용한다.
     TP_BE/.env 예:
       DATABASE_URL=jdbc:postgresql://$PGHOST:$PGPORT/$TARGET_DB
       DB_USER=tp_backend
       FLYWAY_USER=tp_owner
       (DB_PASSWORD, FLYWAY_PASSWORD에 각 비밀번호)
  2) 테이블이 생긴 뒤 이 스크립트를 한 번 더 실행해 03 권한과 04 검증을 확인한다.
  3) 계정 비밀번호는 각 서비스 담당에게만 안전하게 전달한다 (배치 tp_batch, AI tp_ai, 백엔드 tp_backend).
EOF
