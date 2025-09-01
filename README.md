9/1 Spotlight 정리
✅ 수정된 것
Likes

구조를 Suggestion과 유사하게 개편

target_type → role에 종속

target_id 제거, target_name 필드 추가 (null=True, blank=True로 안전 마이그레이션 처리)

같은 대상 중복 좋아요 방지

없는 대상 좋아요 시 ValidationError 발생

좋아요 취소(DELETE) 중복 요청 방지 (이미 취소된 경우 에러 반환)

Admin에서 list_display / search_fields 반영 완료

Serializer에서 user.phone_number FK 참조 (source 옵션) 구현

Postings

Artist FK 제거 → Space FK로 교체

Region 자동 제공 (Space 프로필 기반)

posting_image_url 필드 추가

postings/models.py, serializers.py, views.py, urls.py, admin.py 풀버전 작성 완료

마이그레이션/DB

It is impossible to add a non-nullable field 'space' 오류 → null=True, blank=True 임시 허용 (#추후수정 주석 추가)

no such table: likes_like 오류 → DB 초기화 필요성 확인

DB 리셋 절차 정리: db.sqlite3 및 모든 migrations 파일 삭제 → makemigrations & migrate → superuser 재생성

ModuleNotFoundError: django/db/migrations/migration.py 문제 → pip cache purge, venv 재생성, pip install --no-cache-dir로 해결

INSTALLED_APPS 누락 확인, 오타(artistesquipments) 수정

Git

origin + team 두 remote에 브랜치 생성 및 push 명령어 정리 (2509011901 브랜치)

🚧 안 된 것

Like API에서 내역을 보기 쉽게 정리된 테이블/뷰 제공 (현재는 단순 리스트)

Postings에서 Region 자동 제공 로직: 구조만 반영, 실제 Space 참조 자동화 미완

📌 앞으로 할 일
DB/마이그레이션

config/settings.py → INSTALLED_APPS 전체 확인 및 정리

모든 앱에 대해 makemigrations → migrate 재실행

기존 데이터 유지 전략 검토 (nullable vs default vs 초기화)

Suggestions

status 자동화 처리 수준 (기본값: 미확인 → 수락/거절 자동 업데이트 등)

server, receiver 필드를 null=True로 두지 않고 FK 유효성 보장 필요

is_free_allowed: Artist만 체크 가능

is_performed_confirmed: Space만 체크 가능

status 업데이트를 프론트에서 처리할지, 백엔드에서 처리할지 결정

Spaces

phone_number → Users와 자동 연동

atmosphere → TextField → JSONField 전환

카카오맵 연동: place_name, address, zipcode, place_region 자동화

Points

balance 충전/차감 API 로직 구체화 필요

숨고식 정산 플로우 확정 (단순 balance vs 트랜잭션 로그까지 기록)

Likes

현재는 Artist ↔ Space만 허용 → 확장성(Artist ↔ Artist 협업) 고려 필요

UX: 하트 토글 vs 별도 취소 버튼 논의

API 문서화

회원가입 → 메인화면 → 상세화면 → 제안/좋아요 → 알림 → 포인트 → 마이페이지 전체 흐름 기반으로 Notion 표/문서화

👉 요약하면:

오늘은 Likes/Posts 구조 개편, Suggestion 리팩토링, DB/마이그레이션 오류 해결, Git 브랜치 정리까지 완료.

안 된 것은 Like 내역 뷰, Postings region 자동화.

앞으로 할 것은 Suggestions 상태 전환 로직, Points 정산, Spaces 자동화, API 명세 확정.
