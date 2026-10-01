#!/usr/bin/env python3
"""
apply_ai_cpu_pin.py — ghim tiến trình ai_detector (suy luận GPU) vào 1 nhân CPU. Navigation giữ nguyên.

Sửa TẠI CHỖ (có sao lưu <file>.bak_cpupin), chịu được việc bạn đã/chưa áp các bản cập nhật khác:
  1) launch/amr_ai.launch.py
       - thêm launch argument  ai_cpus  (mặc định "1"; để trống = không ghim)
       - ai_detector khởi động dưới  "taskset -c <ai_cpus>"  -> mọi luồng của nó (DDS, CUDA, TensorRT...) nằm trong nhân đó
       - tự kiểm tra: sai cú pháp / vượt số nhân / thiếu taskset -> KHÔNG ghim và ghi cảnh báo (node vẫn chạy bình thường)
  2) amr_ai/detectors/ai_detector_node.py
       - số luồng OpenCV và torch = số nhân được phép (tránh nhiều luồng tranh nhau 1 nhân)
       - ghi log:  "CPU affinity: [1] -> OpenCV/torch dùng 1 luồng"

Không đụng: Nav2, driver, bringup, nav_fusion, person_tracker, các script start/stop.

Dùng:  python3 apply_ai_cpu_pin.py              xem trước
       python3 apply_ai_cpu_pin.py --apply      thực hiện
       python3 apply_ai_cpu_pin.py --revert     khôi phục từ bản sao lưu
"""
import argparse
import os
import re
import shutil
import sys

MARK_LAUNCH = "def _ai_detector_actions("
MARK_NODE = "def limit_threads_to_allowed_cpus("

HELPERS = '''
def _parse_cpu_list(text):
    """'1' | '1-2' | '0,3-5' -> tập nhân, hoặc None nếu sai cú pháp."""
    cpus = set()
    for part in text.split(','):
        m = re.fullmatch(r'(\\d+)(?:-(\\d+))?', part.strip())
        if not m:
            return None
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        if b < a:
            return None
        cpus.update(range(a, b + 1))
    return cpus


def _ai_detector_actions(context, *args, **kwargs):
    """
    ai_detector = tiến trình suy luận GPU (YOLO person + pose). Ghim vào nhân CPU ai_cpus bằng
    "taskset -c": tiến trình bắt đầu đã ở nhân đó nên mọi luồng sinh sau đều thừa hưởng, và
    khi node khởi động lại vẫn được ghim. ai_cpus rỗng = không ghim.
    """
    ai_cpus = LaunchConfiguration('ai_cpus').perform(context).strip()
    prefix = None

    if not ai_cpus:
        msg = '[ai_detector] ai_cpus rỗng: KHÔNG ghim nhân CPU'
    else:
        cpus = _parse_cpu_list(ai_cpus)
        n = os.cpu_count() or 1
        if cpus is None:
            msg = f'[ai_detector] CẢNH BÁO: ai_cpus="{ai_cpus}" sai cú pháp (vd 1 | 1-2 | 0,3-5) -> KHÔNG ghim'
        elif max(cpus) >= n:
            msg = f'[ai_detector] CẢNH BÁO: ai_cpus="{ai_cpus}" vượt số nhân của máy ({n} nhân) -> KHÔNG ghim'
        elif shutil.which('taskset') is None:
            msg = '[ai_detector] CẢNH BÁO: không tìm thấy lệnh taskset -> KHÔNG ghim'
        else:
            prefix = f'taskset -c {ai_cpus}'
            msg = f'[ai_detector] ghim vào nhân CPU {ai_cpus} (dùng ai_cpus:= để đổi, để trống để tắt)'

    return [
        LogInfo(msg=msg),
        Node(
            package='amr_ai',
            executable='ai_detector',
            name='ai_detector_node',
            output='screen',
            parameters=[LaunchConfiguration('params_file')],
            prefix=prefix,
            condition=IfCondition(LaunchConfiguration('start_ai_detector'))
        ),
    ]


'''

AI_CPUS_ARG = '''
    ai_cpus_arg = DeclareLaunchArgument(
        'ai_cpus',
        default_value='1',
        description='Nhan CPU cho ai_detector (suy luan GPU), vd 1 | 1-2 | 0,3-5. De trong = khong ghim'
    )
'''

NODE_METHOD = '''    def limit_threads_to_allowed_cpus(self):
        """
        Số luồng OpenCV/torch = số nhân CPU được phép (khi ghim bằng taskset chỉ còn 1-2 nhân),
        tránh nhiều luồng thư viện tranh nhau một nhân. Không ghim thì giữ nguyên số nhân của máy.
        """
        try:
            allowed = sorted(os.sched_getaffinity(0))
        except AttributeError:
            return

        n = max(1, len(allowed))
        cv2.setNumThreads(n)
        torch.set_num_threads(n)
        self.get_logger().info(f'CPU affinity: {allowed} -> OpenCV/torch dùng {n} luồng')

'''


def read(path):
    with open(path, encoding='utf-8', newline='') as f:
        return f.read()


def write(path, text):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)


def patch_launch(text):
    if MARK_LAUNCH in text:
        return text, ['đã có sẵn']
    notes = []
    nl = '\r\n' if '\r\n' in text else '\n'
    t = text.replace('\r\n', '\n')

    # 1) import
    if 'OpaqueFunction' not in t:
        t, n = re.subn(r'from launch\.actions import ([^\n]*)', lambda m: f'from launch.actions import {m.group(1)}, OpaqueFunction', t, count=1)
        if not n:
            raise ValueError('không thấy dòng "from launch.actions import ..."')
    for mod in ('re', 'shutil'):
        if not re.search(rf'^import {mod}$', t, re.M):
            t = re.sub(r'^import os$', f'import os\nimport {mod}', t, count=1, flags=re.M)
    notes.append('import')

    # 2) hàm phụ trước generate_launch_description
    if 'def generate_launch_description' not in t:
        raise ValueError('không thấy generate_launch_description')
    t = t.replace('def generate_launch_description', HELPERS.lstrip('\n') + 'def generate_launch_description', 1)
    notes.append('hàm ghim nhân')

    # 3) khai báo ai_cpus sau start_ai_detector_arg
    m = re.search(r'    start_ai_detector_arg = DeclareLaunchArgument\(.*?\n    \)\n', t, re.S)
    if not m:
        raise ValueError('không thấy start_ai_detector_arg')
    t = t[:m.end()] + AI_CPUS_ARG + t[m.end():]
    notes.append('launch argument ai_cpus')

    # 4) thay node ai_detector
    m = re.search(r'    ai_detector = Node\(.*?\n    \)\n', t, re.S)
    if not m:
        raise ValueError('không thấy khối "ai_detector = Node(...)"')
    t = t[:m.start()] + '    ai_detector = OpaqueFunction(function=_ai_detector_actions)\n' + t[m.end():]
    notes.append('ai_detector chạy qua taskset')

    # 5) đưa ai_cpus_arg vào LaunchDescription
    if 'ai_cpus_arg,' not in t:
        t, n = re.subn(r'(        start_ai_detector_arg,\n)', r'\1        ai_cpus_arg,\n', t, count=1)
        if not n:
            raise ValueError('không thấy start_ai_detector_arg trong LaunchDescription')

    return t.replace('\n', nl), notes


def patch_node(text):
    if MARK_NODE in text:
        return text, ['đã có sẵn']
    nl = '\r\n' if '\r\n' in text else '\n'
    t = text.replace('\r\n', '\n')
    for need in ('import os', 'import cv2', 'import torch'):
        if not re.search(rf'^{need}$', t, re.M):
            raise ValueError(f'thiếu "{need}" trong ai_detector_node.py')
    m = re.search(r"        super\(\).__init__\('ai_detector_node'\)\n", t)
    if not m:
        raise ValueError("không thấy super().__init__('ai_detector_node')")
    t = t[:m.end()] + '        self.limit_threads_to_allowed_cpus()\n' + t[m.end():]
    m = re.search(r'    def resolve_model_path\(', t)
    if not m:
        raise ValueError('không thấy resolve_model_path')
    t = t[:m.start()] + NODE_METHOD + t[m.start():]
    return t.replace('\n', nl), ['giới hạn luồng OpenCV/torch + log CPU affinity']


TARGETS = (
    ('launch/amr_ai.launch.py', patch_launch),
    ('amr_ai/detectors/ai_detector_node.py', patch_node),
)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Ghim ai_detector vào 1 nhân CPU')
    ap.add_argument('--ws', default=os.path.expanduser('~/mobile_robot/ros2_ws'))
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--revert', action='store_true')
    args = ap.parse_args(argv)
    pkg = os.path.join(os.path.expanduser(args.ws), 'src', 'amr_ai')

    if args.revert:
        for rel, _fn in TARGETS:
            path = os.path.join(pkg, rel)
            bak = path + '.bak_cpupin'
            if os.path.exists(bak):
                shutil.copy2(bak, path)
                print(f'  đã khôi phục  {rel}')
            else:
                print(f'  (không có bản sao lưu) {rel}')
        print('Sau đó: colcon build --symlink-install --packages-select amr_ai (launch file cần build lại)')
        return 0

    # Tính trước TẤT CẢ các bản sửa; chỉ ghi khi mọi file đều sửa được (tránh sửa dở dang).
    plans, rc = [], 0
    for rel, fn in TARGETS:
        path = os.path.join(pkg, rel)
        if not os.path.exists(path):
            print(f'  (không có)    {rel}')
            rc = 2
            continue
        old = read(path)
        try:
            new, notes = fn(old)
        except ValueError as exc:
            print(f'  LỖI           {rel}: {exc} (file khác bản dự kiến)')
            rc = 2
            continue
        if new == old:
            print(f'  đã áp từ trước {rel}')
            continue
        print(f'  sửa           {rel}: ' + ', '.join(notes))
        plans.append((path, new))

    if rc != 0:
        print('KHÔNG sửa gì cả vì có file không khớp bản dự kiến. Gửi mình file đó để chỉnh bản vá.')
        return rc
    if args.apply:
        for path, new in plans:
            shutil.copy2(path, path + '.bak_cpupin')
            write(path, new)
        print('ĐÃ ÁP DỤNG.' if plans else 'Không có gì để sửa.')
        if plans:
            print('Tiếp theo:  cd ~/mobile_robot/ros2_ws && colcon build --symlink-install --packages-select amr_ai && source install/setup.bash')
            print('Kiểm tra :  sau khi NAVIGATION lên -> taskset -cp $(pgrep -f "lib/amr_ai/ai_detector" | head -1)   (phải ra "... list: 1")')
    else:
        print('XEM TRƯỚC (thêm --apply để sửa).')
    return rc

if __name__ == '__main__':
    sys.exit(main())
