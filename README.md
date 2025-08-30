저는 날짜,시간을 브랜치 명으로하고, 변동 사항을 리드미에 적겠습니다(리드미보다 확인이 편한 방법이 있다면 Let me know......)

## 📌 최근 해결한 주요 문제들 (2025-08-30)

### 1. User ↔ Artist/Space 중복 선택 방지
- `Artist.user`, `Space.user`를 `OneToOneField`로 수정
- `save()`에서 `role` 검증 로직 추가  
  → **Artist에는 artist 계정만**, **Space에는 space 계정만 등록 가능**

### 2. Artist 카테고리 중복 문제 (`new_category` vs `custom_category`)
- 기존 `new_category` 필드는 API에서 중복 입력창으로 노출됨
- `new_category` 제거 → `custom_category`만 유지  
- 필요 시 `categories` API를 통해 직접 입력/등록하도록 구조 단순화

### 3. OAuth ID 명칭 논의
- 현재는 카카오만 사용하기 때문에 `kakao_id`를 유지
- 다중 소셜 로그인 확장 시 `oauth_provider` + `oauth_id` 구조로 개선 예정

### 4. Space 사업자등록번호
- `business_registration_number` 필드 추가
- 유효성 검사 (`10자리 숫자`, `unique=True`)
- Space 등록 시 필수값으로 점진적 적용 예정

### 5. 포인트 시스템 구축
- `PointTransaction` 모델 새로 생성
- 아티스트 전용 포인트 충전/차감 내역 기록
- `balance` 계산 속성 및 API 구현  
  - **POST /api/v1/points/** : 충전/차감  
  - **GET /api/v1/points/{user_id}/balance/** : 현재 잔액 조회
- 프론트/관리자 모두 충전/차감 내역 확인 가능
