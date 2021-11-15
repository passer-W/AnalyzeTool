# encoding: UTF-8
import json
import os
import time
import configparser
import re
import webbrowser
from threading import Thread

key = ""
filter_keys = []
ext = ""
root_dir = ""
result_list = []
template_html_file = ""
key_list = []

file_temp = {
    "id": "1",
    "name": "111.php",
    "path": "222",
    "content": "aaa",
    "preview_content": {
        "<span class='emphasize'>222</span>333": "222"
    },
    "file_content": {
        "<span class='emphasize'>222</span>333": "222"
    },
    "view": False,
    "const": False,
    "lock": False
}

config = configparser.ConfigParser()
config.read("config.ini")
l_gap = int(config.get("SETTING", "l_gap"))
r_gap = int(config.get("SETTING", "r_gap"))
thread = int(config.get("SETTING", "thread"))
reg_cap = False
allow_cover = False
count = 0


class Analyze(Thread):
    def __init__(self, file_name, file_path, file_content):
        Thread.__init__(self)
        self.file_name = file_name
        self.file_path = file_path
        self.line_list = file_content.split(b"\n")
        self.count = 0

    def run(self):
        def append_result():
            nonlocal line
            global count
            if not self.count:
                print(f"\033[33m[*]{self.file_path}".replace("\\", "/"))
                self.count += 1
            for k, v in preview_content.items():
                try:
                    if reg_cap:
                        print("\033[00m%-6d %s" % (int(v), (html2text(k).replace(key, f"\033[31m{key}\033[00m"))))
                    else:
                        i_key_str = html2text(k)
                        for _k in key_list:
                            i_key_str = i_key_str.replace(_k, f"\033[31m{_k}\033[00m")
                        print("\033[00m%-6d %s" % (int(v), html2text(i_key_str).replace(key, f"\033[31m{key}\033[00m")))
                except Exception:
                    pass
            print("-" * 60)
            count += 1
            result_list.append(json.dumps({
                "id": count,
                "name": self.file_name,
                "path": f"{self.file_path}",
                "content": content,
                "preview_content": preview_content,
                "line_content": line_content,
                "view": False,
                "lock": False,
                "name_copy": 0,
                "path_copy": 0,
            }))

        global result_list
        line_num = 0
        line_list = [i.decode('utf-8', errors='ignore').rstrip() for i in
                     self.line_list]
        for line in line_list:
            try:
                line = line.lstrip()
                index = find_str(line, key)
                if index != -1:
                    if len(line) < 200:
                        preview_content, content = get_key_str(line_list, line_num)
                        line_content = {
                            text2html(line): line_num + 1
                        }
                        append_result()
                    else:
                        while index != -1:
                            preview_content, content = get_long_line(line, line_num, index)
                            line_content = {
                                text2html("... " if index > 30 else "") + \
                                line[(index - 30 if index > 30 else 0): index + 30].strip() + \
                                (" ..." if index + 30 < len(line) - 1 else ""): line_num + 1
                            }
                            append_result()
                            index = find_str(line, key, index + 150)
            finally:
                line_num += 1


def find_str(text, keyword, start=0):
    if reg_cap:
        index = text.find(keyword, start)
    else:
        index = text.lower().find(keyword.lower(), start)
        if not index == -1 and text[index:index + len(key)] != key and not text[index:index + len(key)] in key_list:
            key_list.append(text[index:index + len(key)])
    return index


# 获取前后区域的字符串
def get_key_str(file, line_num):
    preview_content = {}
    content = ""
    start_line = line_num - l_gap if line_num - l_gap > 0 else 0
    index = 0
    for i in file[start_line: line_num + r_gap]:
        html_line = text2html(i)
        while html_line in preview_content:
            html_line += " "
        preview_content[html_line] = start_line + index + 1
        content += (html_line + "\n")
        index += 1
    return preview_content, content


def get_long_line(line, line_num, index):
    preview_content = {}
    start = index - 180 if index > 180 else 0
    count = 0
    content = ""
    while (start < len(line)) and count < 7:
        html_line = text2html(line[start: start + 60])
        preview_content[html_line] = line_num + 1
        content += (html_line + "\n")
        start += 60
        count += 1
    return preview_content, content


def text2html(text: str):
    return text.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")


def html2text(text: str):
    return text.replace("&lt;", "<").replace("&gt;", ">").replace("<br>", "<\n>")


def get_pure_text(text):
    return text.replace("-$ls$-", "").replace("-$le$-", "    ")


def get_temp_html():
    file = open("template/template.html", "rb").read()
    return file.decode()


def analyze_file():
    analyze_list = []
    for r, d, fs in os.walk(root_dir):
        for f in fs:
            if ext:
                if not ("." in f and f.split(".")[-1] in ext):
                    continue
            r = r.strip("\\") + "\\"
            try:
                file_content = open(f"{r}{f}", "rb").read()
            except:
                pass
            if filter_keys:
                flag = False
                for i in filter_keys:
                    if i in f or i.encode() in file_content:
                        flag = True
                if flag:
                    continue
            analyze_list.append(Analyze(file_name=f, file_path=f"{r}{f}", file_content=file_content))
            if len(analyze_list) % thread == 0:
                for i in analyze_list:
                    i.start()
                for i in analyze_list:
                    i.join()
                analyze_list = []
    for i in analyze_list:
        i.start()
    for i in analyze_list:
        i.join()
    return True


def save_results():
    count = 1
    push_str = """root.files.push({file_list_str})"""
    file_list_str = ",".join(result_list)
    push_str = push_str.format(file_list_str=file_list_str)
    result_file_name = f"result/%s.html" % (root_dir.split("\\")[-1])
    if not allow_cover:
        while os.path.exists(result_file_name):
            result_file_name = f"result/%s_%d.html" % (root_dir.split("\\")[-1], count)
            count += 1
    result_file = open(result_file_name, "wb")
    result_file.write(
        template_html_file.replace("$major_key$", key).replace("$push_str$", push_str).replace("$reg_cap$",
                                                                                               "true" if reg_cap else "false").encode())
    return result_file_name


def analyze(f_root_dir, f_key, f_ext, f_filter="", f_reg_cap=True, f_allow_cover=False):
    global count, root_dir, key, ext, result_list, reg_cap, allow_cover, template_html_file, key_list, filter_keys
    if not (f_root_dir and os.path.exists(f_root_dir)):
        raise Exception("请输入有效根路径")
    if not f_key:
        raise Exception("请输入有效关键词")
    count = 0
    result_list = []
    root_dir = f_root_dir.replace("/", "\\").strip("\\")
    key = f_key
    if f_filter:
        filter_keys = f_filter.split(",")
    else:
        filter_keys = []
    key_list = [key]
    ext = f_ext
    reg_cap = f_reg_cap
    allow_cover = f_allow_cover
    if not template_html_file:
        template_html_file = get_temp_html()

    start = time.time()
    analyze_file()
    result_list = sorted(result_list, key=lambda x: json.loads(x)["name"])
    result_file_name = save_results()
    all_time = "%.2f" % (time.time() - start)
    print(f"\033[32m[+]分析完毕，用时{all_time}s，共有{count}条匹配数据，结果保存在{result_file_name}文件中")
    return all_time, count, result_file_name


if __name__ == '__main__':
    analyze("F:\测试程序\Panabit\Panabit_SMB\PanabitSMB_SUIr1p7_20210827_FreeBSD9", "download", "", f_filter="", f_allow_cover=False, f_reg_cap=True)

    # webbrowser.open(f"file://{os.getcwd()}/{result_file_name}")
