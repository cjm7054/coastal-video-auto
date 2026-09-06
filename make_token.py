"""로컬에서 1회 실행 → 브라우저 로그인 → token.json 생성.
생성된 token.json 내용을 GitHub Secrets의 YT_TOKEN_JSON에 붙여넣으세요."""
from pipeline.common import load_config
from pipeline.step6_upload import _service
_service(load_config())
print("token.json 생성 완료 → 파일 내용을 GitHub Secret YT_TOKEN_JSON 에 등록하세요")
