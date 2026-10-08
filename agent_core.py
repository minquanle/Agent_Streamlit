from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI


# 1. Hai công cụ đã học trong bài Agent_tool.
@tool
def calculator(a: float, b: float, operation: str) -> str:
    """Tính hai số. operation nhận add, subtract, multiply hoặc divide."""
    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        if b == 0:
            return "Lỗi: không thể chia cho 0."
        result = a / b
    else:
        return "Lỗi: operation không hợp lệ."
    return str(result)


@tool
def count_words(text: str) -> str:
    """Đếm các phần tử tách bởi khoảng trắng bằng text.split()."""
    return f"Đoạn văn có {len(text.split())} từ theo cách tách khoảng trắng."


TOOLS = [calculator, count_words]
TOOL_MAP = {item.name: item for item in TOOLS}


# 2. Lịch sử cho mô hình: tối đa 5 lượt thành công, rồi câu hỏi mới.
def build_history(turns: list, prompt: str) -> list:
    history = []
    completed = [turn for turn in turns if turn.get("reply")]
    for turn in completed[-5:]:
        history.extend([HumanMessage(content=turn["prompt"]),
                        AIMessage(content=turn["reply"])])
    return history + [HumanMessage(content=prompt)]


def text_content(content) -> str:
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") for part in content
                   if isinstance(part, dict) and part.get("type") == "text")


# 3. Vòng lặp Agent: gọi mô hình, chạy tool, đưa kết quả trở lại.
def run_agent(history: list, api_key: str, model_name: str) -> tuple[str, list]:
    model = ChatGoogleGenerativeAI(
        model=model_name, api_key=api_key, vertexai=False,
        timeout=30, max_retries=0,
    ).bind_tools(TOOLS)
    messages = [SystemMessage(content=(
        "Trả lời tiếng Việt, ngắn gọn. Dùng calculator khi tính toán; "
        "dùng count_words khi đếm từ. Không bịa kết quả công cụ. "
        "Đếm từ trong bài này là đếm phần tử tách bởi khoảng trắng. "
        "Không suy đoán thông tin cá nhân nếu lịch sử không có."
    ))] + list(history)
    events = []
    for _ in range(5):
        answer = model.invoke(messages)
        messages.append(answer)
        if not answer.tool_calls:
            reply = text_content(answer.content).strip()
            if not reply:
                raise RuntimeError("Mô hình trả về nội dung rỗng.")
            return reply, events
        for call in answer.tool_calls:
            name, args = call["name"], call["args"]
            if name in TOOL_MAP:
                output = str(TOOL_MAP[name].invoke(args))
            else:
                output = f"Lỗi: công cụ {name} không tồn tại."
            events.append({"tool": name, "args": args, "result": output})
            messages.append(ToolMessage(content=output,
                                        tool_call_id=call["id"]))
    raise RuntimeError("Agent đã đạt giới hạn 5 lần gọi mô hình.")
