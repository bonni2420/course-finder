from django.core.management.base import BaseCommand

from resources.models import Category


class Command(BaseCommand):
    help = "Seed sample categories for course resources."

    def handle(self, *args, **options):
        categories = [
            {
                "name": "Kinh doanh",
                "description": "Kiến thức về quản lý, marketing, tài chính, khởi nghiệp và phát triển kinh doanh.",
            },
            {
                "name": "Ngoại ngữ",
                "description": "Các khóa học tiếng Anh, tiếng Trung, tiếng Nhật, tiếng Hàn và nhiều ngôn ngữ khác cho mọi trình độ.",
            },
            {
                "name": "Lập trình",
                "description": "Học lập trình từ cơ bản đến nâng cao: Python, JavaScript, backend, frontend và phát triển ứng dụng.",
            },
            {
                "name": "Data Science",
                "description": "Phân tích dữ liệu, machine learning, thống kê ứng dụng và công cụ trực quan hóa dữ liệu.",
            },
            {
                "name": "Thiết kế",
                "description": "UI/UX, thiết kế đồ họa, thiết kế sản phẩm và các kỹ năng sáng tạo khác.",
            },
            {
                "name": "Kỹ năng mềm",
                "description": "Luyện kỹ năng thuyết trình, làm việc nhóm, tư duy phân tích, quản lý thời gian.",
            },
        ]

        created_count = 0
        updated_count = 0
        for item in categories:
            _, created = Category.objects.update_or_create(
                name=item["name"],
                defaults={"description": item["description"]},
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed done. Created: {created_count}, Updated: {updated_count}, Total: {len(categories)}"
            )
        )
