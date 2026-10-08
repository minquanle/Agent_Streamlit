import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, ToolMessage

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from agent_core import build_history, run_agent

checks = []
(root / 'tests/results').mkdir(parents=True, exist_ok=True)
def fake_run(answers):
    model = MagicMock()
    model.invoke.side_effect = answers
    constructor = MagicMock()
    constructor.return_value.bind_tools.return_value = model
    return constructor, model

first = AIMessage(content='', tool_calls=[
    {'name': 'count_words', 'args': {'text': 'Hoc AI rat vui'}, 'id': 'wc-1'},
    {'name': 'calculator', 'args': {'a': 123, 'b': 456, 'operation': 'multiply'}, 'id': 'calc-1'},
])
constructor, model = fake_run([first, AIMessage(content=[{'type': 'text', 'text': 'Kết quả đúng.'}])])
with patch('agent_core.ChatGoogleGenerativeAI', constructor):
    reply, events = run_agent(build_history([], 'Kiểm tra'), 'fake-key', 'test-model')
assert reply == 'Kết quả đúng.' and len(events) == 2
messages = model.invoke.call_args.args[0]
assert [m.tool_call_id for m in messages if isinstance(m, ToolMessage)] == ['wc-1', 'calc-1']
assert model.invoke.call_count == 2
checks.append('Nhiều tool trong một phản hồi; ghép đúng ID kết quả; nội dung dạng block.')

constructor, model = fake_run([AIMessage(content='', tool_calls=[
    {'name': 'unknown_tool', 'args': {}, 'id': 'unknown-1'}]), AIMessage(content='Không có công cụ.')])
with patch('agent_core.ChatGoogleGenerativeAI', constructor):
    reply, events = run_agent([], 'fake-key', 'test-model')
assert 'không tồn tại' in events[0]['result']
checks.append('Tên tool lạ được trả thành kết quả lỗi có ID tương ứng.')

constructor, model = fake_run([AIMessage(content='')])
with patch('agent_core.ChatGoogleGenerativeAI', constructor):
    try:
        run_agent([], 'fake-key', 'test-model')
        raise AssertionError('Empty response incorrectly succeeded')
    except RuntimeError as exc:
        assert 'rỗng' in str(exc)
checks.append('Phản hồi rỗng trở thành ngoại lệ để UI hiển thị.')

constructor, model = fake_run([first] * 5)
with patch('agent_core.ChatGoogleGenerativeAI', constructor):
    try:
        run_agent([], 'fake-key', 'test-model')
        raise AssertionError('Loop limit missing')
    except RuntimeError as exc:
        assert '5 lần' in str(exc)
assert model.invoke.call_count == 5
checks.append('Vòng lặp tool chưa kết thúc dừng sau đúng 5 lần gọi mô hình.')

(root / 'tests/results/agent_checks.json').write_text(json.dumps({
    'passed': len(checks), 'checks': checks, 'method': 'Mocked model; actual Python tools executed.'
}, ensure_ascii=False, indent=2), encoding='utf-8')
print('\n'.join('PASS: ' + check for check in checks))
