from resources.services.category_service import render_categories_message

SUPPORTED_CATEGORY_COMMANDS = {"/categories", "categories", "/danhmuc", "danhmuc"}
SUPPORTED_START_COMMANDS = {"/start", "start"}


def build_reply(command_text: str) -> str:
    if command_text in SUPPORTED_CATEGORY_COMMANDS:
        return render_categories_message()

    if command_text in SUPPORTED_START_COMMANDS:
        return "Chào bạn. Gửi /categories để xem danh mục khóa học."

    return "Lệnh chưa hỗ trợ. Gửi /categories để xem danh mục khóa học."
