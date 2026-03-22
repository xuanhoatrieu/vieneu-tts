"""
Seed data — create admin user, system sentence sets, and audio configs.
Run: cd web/backend && python -m app.utils.seed
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from passlib.context import CryptContext
from sqlalchemy import select

from app.core.database import async_session
from app.core.config import settings
from app.models.user import User
from app.models.sentence import SentenceSet, Sentence
from app.models.audio_config import AudioConfig


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── System Sentence Sets ────────────────────────────────────────

SYSTEM_SENTENCES_VI_BASIC = [
    "Xin chào, tôi là VieNeu, trợ lý giọng nói tiếng Việt.",
    "Hà Nội là thủ đô của Việt Nam, nơi có hồ Hoàn Kiếm nổi tiếng.",
    "Hôm nay thời tiết thật đẹp, trời xanh trong và gió mát.",
    "Chúc mừng năm mới, kính chúc quý vị sức khỏe và hạnh phúc.",
    "Cảm ơn bạn đã sử dụng dịch vụ của chúng tôi.",
    "Phở bò là món ăn truyền thống nổi tiếng của Việt Nam.",
    "Tôi rất vui được gặp bạn hôm nay.",
    "Thành phố Hồ Chí Minh là trung tâm kinh tế lớn nhất cả nước.",
    "Mời bạn ngồi xuống và thưởng thức tách cà phê.",
    "Việt Nam có nhiều danh lam thắng cảnh đẹp.",
    "Bạn có thể cho tôi biết đường đến bưu điện không?",
    "Tôi muốn đặt một bàn cho hai người vào tối nay.",
    "Chương trình khuyến mãi giảm giá năm mươi phần trăm.",
    "Xin lỗi, tôi đến muộn vì tắc đường.",
    "Cuốn sách này rất hay, tôi đã đọc nó hai lần.",
    "Ngày mai là thứ bảy, chúng ta đi dã ngoại nhé.",
    "Tôi đã sống ở Đà Nẵng được năm năm rồi.",
    "Mưa rơi nhẹ trên mái ngói, tiếng mưa thật êm dịu.",
    "Trẻ em hôm nay là tương lai của đất nước ngày mai.",
    "Tôi thích nghe nhạc trữ tình vào buổi tối.",
    "Con đường dẫn đến thành công không bao giờ dễ dàng.",
    "Bác sĩ khuyên tôi nên tập thể dục mỗi ngày.",
    "Mùa xuân đến, hoa mai nở vàng rực rỡ.",
    "Chúng ta cần bảo vệ môi trường cho thế hệ tương lai.",
    "Tôi vừa hoàn thành dự án nghiên cứu sau ba tháng làm việc.",
    "Giáo dục là chìa khóa mở ra cánh cửa tương lai.",
    "Biển Nha Trang trong xanh và bãi cát trắng mịn.",
    "Anh ấy luôn đúng giờ và làm việc rất chăm chỉ.",
    "Tôi cần gặp giám đốc để thảo luận về kế hoạch mới.",
    "Cô ấy hát rất hay, giọng hát trong trẻo và ngọt ngào.",
    "Việt Nam có bốn mùa rõ rệt: xuân, hạ, thu, đông.",
    "Tôi sẽ gọi lại cho bạn vào lúc ba giờ chiều.",
    "Nhà hàng này phục vụ các món ăn Việt Nam truyền thống.",
    "Chúng tôi xin gửi lời cảm ơn chân thành nhất.",
    "Hãy luôn giữ nụ cười trên môi và sự lạc quan trong lòng.",
    "Tháng bảy âm lịch là mùa Vu Lan báo hiếu.",
    "Tôi đã đi du lịch Huế và tham quan nhiều di tích lịch sử.",
    "Công nghệ trí tuệ nhân tạo đang phát triển rất nhanh.",
    "Xin vui lòng để lại lời nhắn sau tiếng bíp.",
    "Chào mừng bạn đến với chương trình phát thanh buổi sáng.",
    "Tôi muốn mua một chiếc áo dài màu đỏ.",
    "Đội tuyển bóng đá Việt Nam đã giành chiến thắng.",
    "Ông bà tôi sống ở quê, trồng lúa và nuôi cá.",
    "Sinh viên năm cuối đang chuẩn bị cho kỳ thi tốt nghiệp.",
    "Tôi rất thích ẩm thực Việt Nam vì nó vừa ngon vừa lành.",
    "Hãy đeo khẩu trang và rửa tay thường xuyên.",
    "Chúc bạn có một ngày tốt lành và nhiều niềm vui.",
    "Tôi đang tìm kiếm một căn hộ ở trung tâm thành phố.",
    "Đây là bản tin thời sự lúc mười hai giờ trưa.",
    "Cảm ơn đã lắng nghe, hẹn gặp lại trong chương trình tới.",
]

SYSTEM_SENTENCES_REF = [
    "Xin chào, tôi là VieNeu.",
    "Hôm nay trời thật đẹp.",
    "Cảm ơn bạn rất nhiều.",
    "Tôi rất vui được gặp bạn.",
    "Chúc bạn một ngày tốt lành.",
    "Mời bạn ngồi xuống đây.",
    "Đó là một ý tưởng hay.",
    "Tôi hiểu rồi, cảm ơn nhé.",
    "Hẹn gặp lại bạn sau.",
    "Xin chào và tạm biệt.",
]


async def seed():
    """Run all seed operations."""
    async with async_session() as db:
        # ─── 1. Admin User ─────────────────────────
        result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        admin = result.scalar_one_or_none()

        if not admin:
            admin = User(
                email=settings.ADMIN_EMAIL,
                password_hash=pwd_context.hash(settings.ADMIN_PASSWORD),
                name="Admin",
                role="admin",
            )
            db.add(admin)
            await db.flush()
            print(f"✅ Admin user created: {settings.ADMIN_EMAIL}")
        else:
            print(f"⏩ Admin user already exists: {settings.ADMIN_EMAIL}")

        # ─── 2. System Sentence Sets ────────────────
        result = await db.execute(
            select(SentenceSet).where(SentenceSet.is_system == True)
        )
        existing_sets = result.scalars().all()

        if not existing_sets:
            # Basic Vietnamese set (50 sentences)
            basic_set = SentenceSet(
                name="Bộ câu tiếng Việt cơ bản",
                description="50 câu tiếng Việt đa dạng để thu âm finetune. Bao gồm: giới thiệu, chào hỏi, kể chuyện, tin tức, đời sống.",
                category="basic",
                language="vi",
                is_system=True,
            )
            db.add(basic_set)
            await db.flush()

            for i, text in enumerate(SYSTEM_SENTENCES_VI_BASIC):
                db.add(Sentence(set_id=basic_set.id, text=text, order_index=i + 1))
            print(f"✅ System set created: '{basic_set.name}' ({len(SYSTEM_SENTENCES_VI_BASIC)} câu)")

            # Ref audio set (10 short sentences)
            ref_set = SentenceSet(
                name="Ref audio tối ưu",
                description="10 câu ngắn 3-5 giây, tối ưu cho zero-shot voice cloning. Câu ngắn, đa dạng ngữ điệu.",
                category="ref",
                language="vi",
                is_system=True,
            )
            db.add(ref_set)
            await db.flush()

            for i, text in enumerate(SYSTEM_SENTENCES_REF):
                db.add(Sentence(set_id=ref_set.id, text=text, order_index=i + 1))
            print(f"✅ System set created: '{ref_set.name}' ({len(SYSTEM_SENTENCES_REF)} câu)")
        else:
            print(f"⏩ System sentence sets already exist ({len(existing_sets)} sets)")

        # ─── 3. Audio Configs ────────────────────────
        result = await db.execute(select(AudioConfig))
        existing_configs = result.scalars().all()

        if not existing_configs:
            configs = [
                AudioConfig(
                    name="recording",
                    sample_rate=24000,
                    channels=1,
                    format="wav",
                    min_duration=1.0,
                    max_duration=30.0,
                    description="Audio thu âm qua browser hoặc upload.",
                ),
                AudioConfig(
                    name="ref_audio",
                    sample_rate=24000,
                    channels=1,
                    format="wav",
                    min_duration=3.0,
                    max_duration=15.0,
                    description="Reference audio tối ưu cho zero-shot voice cloning.",
                ),
                AudioConfig(
                    name="training",
                    sample_rate=16000,
                    channels=1,
                    format="wav",
                    min_duration=3.0,
                    max_duration=15.0,
                    description="Audio tối ưu cho NeuCodec encode + LoRA training.",
                ),
            ]
            db.add_all(configs)
            print(f"✅ Audio configs created: {len(configs)} configs")
        else:
            print(f"⏩ Audio configs already exist ({len(existing_configs)} configs)")

        await db.commit()
        print("\n🎉 Seed complete!")


if __name__ == "__main__":
    asyncio.run(seed())
