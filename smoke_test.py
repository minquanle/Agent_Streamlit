from agent_core import build_history, calculator, count_words

assert calculator.invoke({"a": 123, "b": 456,
                          "operation": "multiply"}) == "56088.0"
assert "4 từ" in count_words.invoke({"text": "Hoc AI rat vui"})
assert "Lỗi" in calculator.invoke({"a": 1, "b": 0, "operation": "divide"})
for a, b in ((float("inf"), 1), (float("nan"), 1), (1e308, 1e308)):
    assert "Lỗi" in calculator.invoke({"a": a, "b": b, "operation": "multiply"})
turns = [{"prompt": f"Câu {i}", "reply": f"Đáp {i}"} for i in range(7)]
turns.append({"prompt": "Câu lỗi", "reply": "", "error": "API lỗi"})
history = build_history(turns, "Câu mới")
assert len(history) == 11 and history[0].content == "Câu 2"
assert history[-1].content == "Câu mới"
assert len(build_history([], "Xin chào")) == 1
print("PASS: 123*456=56088; đếm 4 từ; chia 0 trả thông báo lỗi.")
print("PASS: giữ 5 lượt thành công; bỏ lượt lỗi; câu mới có đúng một lần.")
print("PASS: từ chối inf/nan và báo lỗi khi kết quả tràn số thực.")
