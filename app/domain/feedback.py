from app.models.schemas import FeedbackRequest


class FeedbackDomain:
    """
    負責處理自學習機制的業務規則。
    將「如何判斷優質回答」的邏輯從 API 層抽離到此處。
    """

    @staticmethod
    def is_worthy_for_learning(fb: FeedbackRequest) -> bool:
        """
        判斷此回饋是否具備學習價值。

        規則：
        1. 評分必須大於或等於 4 分 (滿分 5)。
        2. 問題與回答的內容不能為空。
        3. (選填) 可以加入內容長度檢查，避免過短的無意義回答被存入。
        """
        # 基本分數檢查
        if fb.score < 4:
            return False

        # 內容完整性檢查
        if len(fb.query.strip()) < 2 or len(fb.answer.strip()) < 5:
            return False

        # 未來可以擴充：例如檢查是否包含「我不知道」等負面字眼
        blacklist = ["不知道", "找不到", "抱歉", "sorry"]
        if any(word in fb.answer for word in blacklist):
            return False

        return True

    @staticmethod
    def format_for_gold_standard(fb: FeedbackRequest) -> str:
        """
        格式化存入金標庫的文本。
        """
        return f"問題: {fb.query}\n優質回答: {fb.answer}"
