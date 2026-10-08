import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

root = Path(__file__).resolve().parents[1]
project = root
sys.path.insert(0, str(project))
import agent_core

checks = []
(root / 'tests/results').mkdir(parents=True, exist_ok=True)
with patch('dotenv.load_dotenv', return_value=False), patch.dict(os.environ, {'GOOGLE_API_KEY': '', 'DEBUG': 'true'}):
    app = AppTest.from_file(str(project / 'app.py'), default_timeout=15).run()
    assert not app.exception
    app.chat_input[0].set_value('Xin chào').run()
    assert not app.exception and 'Chưa có' in app.error[0].value
    assert len(app.session_state['turns']) == 1
    app.text_input[1].set_value('another-model').run()
    assert not app.exception and 'Chưa có' in app.error[0].value
    assert app.session_state['turns'][0]['details'].startswith('Traceback')
    checks.append('Thiếu key: lỗi và traceback thật; không gọi API; lỗi tồn tại qua rerun.')
    app.button[0].click().run()
    assert app.session_state['turns'] == [] and len(app.error) == 0
    checks.append('Nút xóa dọn lịch sử và lỗi.')

    app.text_input[0].set_value('unit-test-only-key').run()
    with patch.object(agent_core, 'run_agent') as remote:
        app.chat_input[0].set_value('   ').run()
        assert not app.exception and remote.call_count == 0
        assert app.session_state['turns'] == [] and len(app.warning) == 1
    checks.append('Chỉ có khoảng trắng: cảnh báo, không gọi API và không lưu lượt rỗng.')
    app.text_input[1].set_value('   ').run()
    with patch.object(agent_core, 'run_agent') as remote:
        app.chat_input[0].set_value('Xin chào').run()
        assert not app.exception and remote.call_count == 0
        assert 'không được để trống' in app.error[0].value
    checks.append('Tên model rỗng: lỗi được lưu trước khi gọi API.')
    app.button[0].click().run()
    app.text_input[1].set_value('gemini-3.5-flash-lite').run()
    event = {'tool': 'calculator', 'args': {'a': 123, 'b': 456, 'operation': 'multiply'}, 'result': '56088.0'}
    with patch.object(agent_core, 'run_agent', return_value=('56088', [event])) as remote:
        app.chat_input[0].set_value('123 nhân 456').run()
        assert remote.call_count == 1 and not app.exception
        assert app.session_state['turns'][0]['reply'] == '56088'
        app.text_input[1].set_value('gemini-3.5-flash-lite').run()
        assert remote.call_count == 1
    checks.append('Thành công được lưu; rerun không gọi API lần thứ hai.')

    with patch.object(agent_core, 'run_agent', side_effect=RuntimeError('API key not valid: unit-test-only-key')):
        app.chat_input[0].set_value('Gây lỗi').run()
    assert not app.exception and 'không hợp lệ' in app.error[0].value
    assert 'unit-test-only-key' not in app.session_state['turns'][-1]['details']
    assert 'API_KEY_DA_CHE' in app.session_state['turns'][-1]['details']
    checks.append('Ngoại lệ API: lỗi được lưu; key đã biết được che khỏi traceback.')

    with patch.object(agent_core, 'run_agent', return_value=('Đã phục hồi', [])) as remote:
        app.chat_input[0].set_value('Thử lại').run()
        history = remote.call_args.args[0]
        assert len(history) == 3 and history[-1].content == 'Thử lại'
        assert all(message.content != 'Gây lỗi' for message in history)
    checks.append('Sau lỗi vẫn gửi được; lượt lỗi không gửi lại cho mô hình.')

with patch('dotenv.load_dotenv', return_value=False), patch.dict(os.environ, {'GOOGLE_API_KEY': '', 'DEBUG': 'false'}):
    other = AppTest.from_file(str(project / 'app.py')).run()
    assert not other.exception and other.session_state['turns'] == []
    other.chat_input[0].set_value('Xin chào').run()
    assert 'details' not in other.session_state['turns'][0]
    checks.append('Phiên mới không nhận lịch sử phiên cũ; DEBUG=false không lưu traceback.')

(root / 'tests/results/ui_checks.json').write_text(json.dumps({
    'passed': len(checks), 'checks': checks,
    'method': 'Streamlit AppTest; mocked API for UI failure/rerun invariants only; browser tests use real Gemini separately.',
}, ensure_ascii=False, indent=2), encoding='utf-8')
print('\n'.join('PASS: ' + check for check in checks))
