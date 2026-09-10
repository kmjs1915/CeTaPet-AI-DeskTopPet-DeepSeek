# -*- coding: utf-8 -*-
"""
================================================================================
  鲸鱼娘桌宠（WhaleGirl Desktop Pet）  —  PySide6 实现
--------------------------------------------------------------------------------
  功能总览（严格按需求实现）：
    1. 双击桌宠：无任何动作（不再弹出聊天框）。
    2. 右键桌宠：在鼠标光标位置弹出菜单【聊聊天 / 查询余额 / 添加资料文件 /
       查看已有资料 / 退出】。
    3. 素材目录（以程序基准目录/asset_library 为根）：
         move/idle/{nothing,eat,think}/*.png    —— 待机三态
         move/PickUp/pickup.png                 —— 拖拽
         move/touch/touch.png                   —— 点击
         move/query/nomoney.png                 —— 余额查询
         talk/{touch,nothing}.txt               —— 台词池（每行一条“…”）
         API-KEY.txt                            —— 唯一密钥文件（一行 sk- 开头的 DeepSeek 密钥）
    4. idle 待机状态机：固定周期 5 分钟 nothing(240s) → eat(30s) → think(30s)，
       循环轮转；进入 eat/think 瞬间弹出固定台词；仅 nothing 阶段开启 30s
       待机台词计时器。启动即重置周期，从 nothing 开始，不落盘。
    5. 拖拽(PickUp)：按下+移动超过阈值才算拖拽；拖拽开始瞬间切 pickup.png 并
       只弹一次“你干嘛？放我下来！”；拖拽期间暂停全部待机计时器；松开强制回
       nothing 并接续待机进度。
    6. 点击(touch)：单击切 touch.png 并随机弹 touch.txt 台词；暂停待机计时；
       3 秒内再次点击则清除旧 3 秒计时重新计时；3 秒结束回 nothing 接续待机。
    7. 查询余额(query，右键菜单触发)：主程序内调用 DeepSeek 官方
       GET /user/balance（requests，超时 10 秒，独立线程，不卡界面）；
       成功弹“目前APIKEY剩余：¥ xx.xx元。”，失败弹“余额获取失败，请检查网络
       或APIKEY。”；期间切 nomoney.png、暂停全部待机计时、屏蔽 touch 与拖拽；
       点击任意处退出查询回 nothing 并接续待机。
    8. 聊聊天：右键菜单打开独立聊天子窗口（DeepSeek Chat Completions，异步，
       密钥同样读 asset_library/API_KEY.txt），关窗仅隐藏不退出程序。
     9. 图片动态加载：每次状态切换（idle/touch/pickup/query）实时从磁盘读取
        对应 PNG，不做内存缓存、不强制缩放；窗口跟随图片原生尺寸自动变化，
        气泡按窗口新尺寸自动贴靠。直接替换 asset_library/move/** 下的 png，
        重启程序即生效（无需改代码/重新打包 exe）。
    10. 系统托盘：启动即注册 QSystemTrayIcon 常驻右下角（含 Windows 隐藏图标
        列表）；托盘右键菜单与桌宠右键菜单一致【聊聊天/查询余额/退出】；
        点窗口关闭按钮只隐藏主窗口驻留后台，双击托盘图标还原；仅【退出】执行
        完整退出（停止全部定时器/销毁气泡/销毁托盘）。系统不支持托盘时回退为
        关窗即完全退出。
    11. RAG 文档管理（知识库）：项目根目录 RAG 文件夹（启动自动创建，仅支持
        .txt / .docx）；
        · 添加资料：右键菜单【添加资料文件】多选导入，或把外部文件直接拖到
          桌宠窗口导入（严格区别于鼠标拖拽移动桌宠 PickUp）；合法文件移动到
          RAG（重名自动加序号不覆盖），成功/失败分别切 true.png / wrong.png 并
          弹固定气泡（失败另带 0.3 秒抖动），进入 file_import 状态 3 秒后回 idle；
        · 查看资料：右键菜单【查看已有资料】打开系统资源管理器浏览 RAG 文件夹，
          进入 view_files 状态（think.png + “当前已收纳x个资料”），监听文件夹
          窗口关闭自动回 idle；无法精准监听时，任何点击/拖拽交互即结束该状态；
        · 知识库刷新时机：打开聊天窗口时、每次文件导入成功后；文本合并上限
          20000 字、单文档 8000 字（超出截断，聊天窗小字提示）。
    12. 状态机新增：file_import（文件导入反馈）、view_files（查看资料状态），
        优先级位于 query 之下、idle 之上；高优先级（PickUp/touch/query）状态下
        文件拖拽导入不触发反馈、查看资料命令不切换图片，避免状态错乱。
    13. API 密钥（唯一文件 asset_library/API-KEY.txt；启动最先处理，模态完成才加载桌宠）：
        · 文件已有有效内容 → 直接读取（去首尾空白/换行），【不做连通测试、不弹成功窗】；
        · 文件不存在 / 为空 → 输入弹窗（密码掩码），【先连通测试、通过后才写入】：
          · 测试成功 → 写入 API-KEY.txt → “注册成功！”3 秒自动关闭后启动桌宠；
          · 测试失败 → 不写入文件，聊天框红字“API_KEY有误，请重新输入。”并回到
            输入弹窗供修改；空输入 / 退出程序 → 直接退出（不生成任何密钥文件）；
          · 测试通过但写盘失败（权限）→ 弹窗提示后退出（磁盘不产生密钥文件）；
        · 运行中右键【更改API-KEY】同样【先测试，通过后才覆盖写入】，失败不破坏旧密钥；
        · 旧版本误建的 “API_KEY.txt” 变体会自动迁移清理，只保留 API-KEY.txt 一份。
        · 错误密钥永远不会写入磁盘。
    14. 登场动画 cheerup_show（素材 asset_library/move/cheerup/cheerup.png）：
        · 新用户（密钥测试通过并写入后）与老用户（直接读取文件）启动时均执行；
          从隐藏恢复（托盘双击 / 菜单【显示鲸鱼娘】）也执行；
        · 正式显示后切 cheerup.png + 气泡“DeepSeek鲸鱼娘登场！”（3 秒），
          进入 cheerup_show 状态 3 秒，期间屏蔽触摸/PickUp 拖拽；
        · 3 秒结束切回 idle nothing，此时才启动/恢复待机计时（严禁提前启动）；
        · 素材缺失/损坏 → 警告并跳过效果，立刻进入待机（绝不卡死）；
        · 优先级：…> view_files > cheerup_show > idle，更高优先级可打断。

  全局气泡规则：气泡存在固定 3 秒；新台词立刻销毁上一个气泡（同一时刻仅一个）；
  气泡跟随桌宠位置（桌宠移动、窗口随图片尺寸变化时自动重新贴靠）。

  状态机优先级（高打断/暂停低，结束后回到 idle 接续此前计时进度）：
      PickUp(拖拽) > touch(点击) > query(查询余额) > file_import(资料导入反馈)
      > view_files(查看资料状态) > idle 待机(nothing/eat/think)

  容错：图片缺失/损坏 → 控制台警告 + 空白占位继续运行，不崩溃；
        txt 缺失/为空 → 内置兜底台词；API_KEY.txt 缺失/为空 → 余额提示获取失败。

  网络边界：全部文件读取 / 接口请求都由本地 Python 代码完成，绝不把本地文件
  内容发送给远程模型；密钥只出现在本地 HTTP Authorization 头中，不打印、不上传。

  运行：
      pip install PySide6 requests
      python main.py            # 前台运行（带控制台日志）
  打包（exe 需包含 PySide6 与 requests，PyInstaller 自动收集）：
      pyinstaller -F -w -n WhaleGirlPet --add-data "asset_library;asset_library" main.py
      → 分发时 exe 与 asset_library 文件夹必须同级；替换 exe 同级
        asset_library/move/** 里的 png 即换图，无需修改代码、无需重新打包。
================================================================================
"""

import ctypes
import json
import os
import random
import re
import shutil
import sys
import threading
import xml.etree.ElementTree as ET
import zipfile

import requests
from PySide6.QtCore import (QEventLoop, QObject, QPoint, QPointF,
                            QRect, QRectF, Qt, QTimer, QUrl, Signal)
from PySide6.QtGui import (QAction, QColor, QDragEnterEvent, QDropEvent, QFont,
                           QFontMetrics, QIcon, QPainter, QPen, QPixmap,
                           QPolygon)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (QApplication, QDialog, QFileDialog, QHBoxLayout,
                               QLabel, QLineEdit, QMenu, QMessageBox,
                               QPushButton, QSystemTrayIcon, QTextEdit,
                               QVBoxLayout, QWidget, QWidgetAction)

# ---- 控制台输出编码加固：Windows GBK 控制台打印 “¥/中文” 不再崩溃 ----
for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream is not None and hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 —— pythonw/打包后可能没有控制台
        pass

# ================================================================================
# 一、路径 / 素材 / 台词 / 固定文案 常量
# ================================================================================


def app_base_dir() -> str:
    """运行基准目录：源码=main.py 所在目录；PyInstaller 冻结=exe 所在目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def asset_library_dir() -> str:
    """
    定位 asset_library 素材目录：
      - 源码运行：main.py 同级的 asset_library；
      - PyInstaller 打包：优先 exe 同目录的 asset_library（用户可直接替换图片，
        重启即生效），找不到时回退到打进 exe 的解包目录 _MEIPASS（自包含兜底）。
    依次探测，取第一个真实存在的目录，保证打包/源码两用都不崩溃。
    """
    candidates: list = []
    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(os.path.dirname(sys.executable),
                                       "asset_library"))
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(os.path.join(meipass, "asset_library"))
    else:
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "asset_library"))
    for cand in candidates:
        if os.path.isdir(cand):
            return cand
    return candidates[0]


BASE_DIR: str = app_base_dir()
ASSET_ROOT: str = asset_library_dir()          # 素材根目录

# ---- 图片素材相对路径（相对 asset_library）----
IMAGE_RELS: dict = {
    "nothing": os.path.join("move", "idle", "nothing", "nothing.png"),
    "eat":     os.path.join("move", "idle", "eat", "eat.png"),
    "think":   os.path.join("move", "idle", "think", "think.png"),
    "pickup":  os.path.join("move", "PickUp", "pickup.png"),
    "touch":   os.path.join("move", "touch", "touch.png"),
    "nomoney": os.path.join("move", "query", "nomoney.png"),
    "cheerup": os.path.join("move", "cheerup", "cheerup.png"),  # 登场动画
    "true":    os.path.join("move", "file", "true", "true.png"),      # 导入成功反馈
    "wrong":   os.path.join("move", "file", "wrong", "wrong.png"),    # 导入失败反馈
}

# ---- 右键菜单（桌宠本体与托盘保持一致、严格按此顺序；含一条分隔线与红色【退出】）----
# ---- 窗口位置记忆 config.json（程序运行根目录，运行时生成、不打进包）----
CONFIG_REL: str = "config.json"
CONFIG_PATH: str = os.path.join(BASE_DIR, CONFIG_REL)

# ---- 登场（cheerup_show）固定气泡台词 ----
ENTRANCE_SPEECH: str = "DeepSeek鲸鱼娘登场！"

# ---- RAG 知识库（项目根目录 RAG 文件夹）----
RAG_DIR: str = os.path.join(BASE_DIR, "RAG")
SUPPORTED_EXT: tuple = (".txt", ".docx")     # 仅支持 txt/docx，不支持旧版 .doc
RAG_MAX_TOTAL: int = 20000                   # 全部文档合并总文本上限（字）
RAG_MAX_DOC: int = 8000                      # 单个文档文本上限（字）

# ---- 台词文本相对路径 ----
TALK_TOUCH_REL: str = os.path.join("talk", "touch.txt")
TALK_NOTHING_REL: str = os.path.join("talk", "nothing.txt")

# ---- API 密钥文件命名（严格固定为唯一文件名 API-KEY.txt）----
# 读取 / 写入只操作 asset_library/API-KEY.txt 这一份文件：
# 写入时先判断存在则直接覆盖（open 'w'），绝不新建副本、绝不生成重复 txt。
# 旧版本曾误建 “API_KEY.txt” 变体：这里仅保留读取/迁移兼容，成功写入后自动删除清理。
API_KEY_REL: str = os.path.join("API-KEY.txt")
LEGACY_KEY_REL: str = os.path.join("API_KEY.txt")

# ---- idle 待机状态机（固定顺序轮转，总周期 5 分钟）----
IDLE_ORDER: list = ["nothing", "eat", "think"]
IDLE_MS: dict = {"nothing": 240_000, "eat": 30_000, "think": 30_000}

# ---- 时间常量（毫秒）----
BUBBLE_MS: int = 3000            # 气泡固定存在 3 秒
TOUCH_MS: int = 3000             # touch 交互 3 秒倒计时
IDLE_TALK_MS: int = 30_000       # nothing 阶段每 30s 弹一句待机台词
DRAG_THRESHOLD_PX: int = 10      # 判定为“拖拽”的最小移动距离（像素）
FILE_IMPORT_MS: int = 3000       # file_import 反馈状态持续 3 秒
SHAKE_MS: int = 300              # 导入失败窗口抖动总时长 0.3 秒
SHAKE_STEP_MS: int = 30          # 抖动单步时长（毫秒）
VIEW_POLL_MS: int = 700          # 监听 RAG 文件夹窗口关闭的轮询间隔
VIEW_OPEN_TRIES: int = 20        # 等待资源管理器窗口出现的最大轮询次数(≈14s)
CHEERUP_MS: int = 3000           # cheerup_show 登场状态持续 3 秒

# ---- 固定台词（原样保留）----
EAT_SPEECH: str = "大米饭...好吃！"
THINK_SPEECH: str = "刚刚要干嘛来着？"
PICKUP_SPEECH: str = "你干嘛？放我下来！"
BALANCE_OK_TEXT = "目前APIKEY剩余：¥ {amount:.2f}元。"
BALANCE_FAIL_TEXT = "余额获取失败，请检查网络或APIKEY。"

# ---- RAG / 文件导入相关固定文案 ----
FILE_OK_SPEECH: str = "吃饱了...嗝..."
FILE_FAIL_SPEECH: str = "呕...你给我喂的啥？"
VIEW_COUNT_SPEECH = "当前已收纳{count}个资料"
VIEW_OPEN_FAIL_SPEECH: str = "呜呜...资料文件夹打不开..."
RAG_LABEL_TEXT = "已加载RAG文本：{loaded} / {max}字"

# ---- 兜底台词（txt 缺失 / 为空时使用，保证程序不崩溃）----
TOUCH_FALLBACK: list = [
    "喂！不要随便戳我啊！",
    "别碰我啦！好痛的！",
    "哼，找我有什么事吗？",
]
NOTHING_FALLBACK: list = [
    "好无聊啊……",
    "主人什么时候来找我玩呀？",
    "呼——好困……",
]

# ---- DeepSeek 接口配置 ----
BALANCE_API_URL: str = "https://api.deepseek.com/user/balance"   # 查询余额
CHAT_API_URL: str = "https://api.deepseek.com/v1/chat/completions"  # 聊天
DEEPSEEK_MODEL: str = "deepseek-v4-flash"   # 模型名（可按需修改）
BALANCE_TIMEOUT_S: int = 10                 # 余额请求超时（秒）
CHAT_TIMEOUT_MS: int = 30_000               # 聊天请求超时（毫秒）
CHAT_HISTORY_MAX_MESSAGES: int = 12         # 每次请求保留的最近上下文消息数

# ---- API 密钥：连通性测试 / 文案常量 ----
CONNECTIVITY_API_URL: str = "https://api.deepseek.com/models"  # 轻量连通性测试端点
API_CONNECT_TIMEOUT_S: int = 10             # 连通性测试超时（秒）
KEY_REGISTERED_TEXT: str = "注册成功！"       # 连接成功自动关闭弹窗文案
KEY_INVALID_TEXT: str = "API_KEY有误，请重新输入。"   # 连接失败聊天框红色文案
KEY_EMPTY_HINT: str = "密钥不能为空，请重新输入。"    # 更改密钥时空输入提示

_CURRENT_KEY: str = ""      # 内存中“正在使用”的 DeepSeek API 密钥（启动校验/更改成功后更新）


def set_current_api_key(key: str) -> None:
    """更新内存密钥：后续余额/聊天请求直接使用新密钥（内容保密，不打印）。"""
    global _CURRENT_KEY
    _CURRENT_KEY = (key or "").strip()


def api_key_file_path() -> str:
    """唯一密钥文件路径：asset_library/API-KEY.txt（文件名严格固定）。"""
    return os.path.join(ASSET_ROOT, API_KEY_REL)


def legacy_key_file_path() -> str:
    """旧版本误建的 API_KEY.txt 变体路径（仅读取迁移兼容，正常不再产生）。"""
    return os.path.join(ASSET_ROOT, LEGACY_KEY_REL)


def _read_key_from_file(path: str) -> str:
    """读取单个文件第一行非空内容（去首尾空白/换行）；不存在/为空/异常 → 空串。"""
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            for raw in fh:
                line = raw.strip()          # 自动剔除首尾空白/换行
                if line:
                    return line
    except OSError as exc:
        print(f"[鲸鱼娘] 【警告】密钥文件读取失败：{path}（{exc}）")
        return ""
    return ""


def read_api_key() -> str:
    """
    返回当前有效密钥：优先使用内存缓存（启动通过 / 更改成功后写入的新密钥，
    后续对话直接使用）；内存为空时读取唯一文件 asset_library/API-KEY.txt
    （旧版本 API_KEY.txt 仅作向后兼容读取），自动去除首尾空白/换行。
    全部缺失 / 内容为空 / 读取失败 → 返回空串（不抛异常、不打印密钥内容）。
    """
    if _CURRENT_KEY:
        return _CURRENT_KEY
    key = _read_key_from_file(api_key_file_path())
    if not key:
        key = _read_key_from_file(legacy_key_file_path())   # 旧版兼容读取
    if not key:
        print(f"[鲸鱼娘] 【警告】未找到有效密钥文件（{API_KEY_REL}），"
              "余额查询/聊天将提示获取失败。")
    return key


def _read_existing_api_key_file() -> str:
    """静默探测：唯一文件 API-KEY.txt 有内容 → 去空白密钥；为空/缺失再回退旧版文件。"""
    key = _read_key_from_file(api_key_file_path())
    if not key:
        key = _read_key_from_file(legacy_key_file_path())
    return key


class ApiKeySetupDialog(QDialog):
    """
    程序启动时（未检测到有效 API 密钥）弹出的模态输入对话框：
      - 标题：DeepSeek API密钥设置
      - 提示：本程序仅支持DeepSeek API。请输入你的DeepSeek Api Key。
      - 小字：密钥保存位置：程序目录/asset_library/API-KEY.txt
      - 输入框默认空白 + 掩码（密码框，不明文显示）；
      - 按钮：【确认】/【退出程序】。
    返回 Accepted=点【确认】；Rejected=点【退出程序】或关闭窗口（等同退出程序）。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DeepSeek API密钥设置")
        self.setModal(True)                                  # 模态，必须先处理完才能继续
        self.setWindowModality(Qt.ApplicationModal)
        self.setMinimumWidth(440)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)  # 隐藏“?”帮助按钮

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(10)

        tip = QLabel("本程序仅支持DeepSeek API。请输入你的DeepSeek Api Key。", self)
        tip.setWordWrap(True)
        root.addWidget(tip)

        self._edit = QLineEdit(self)
        self._edit.setEchoMode(QLineEdit.Password)           # 掩码输入，不明文显示
        self._edit.setPlaceholderText("")                     # 默认空白
        root.addWidget(self._edit)

        hint = QLabel("密钥保存位置：程序目录/asset_library/API-KEY.txt", self)
        hint.setStyleSheet("color:#999999;")
        hint.setWordWrap(True)
        root.addWidget(hint)

        row = QHBoxLayout()
        row.addStretch(1)
        self._ok_btn = QPushButton("确认", self)
        self._quit_btn = QPushButton("退出程序", self)
        self._ok_btn.clicked.connect(self.accept)            # 内容非空校验由调用方执行
        self._quit_btn.clicked.connect(self.reject)
        row.addWidget(self._ok_btn)
        row.addWidget(self._quit_btn)
        root.addLayout(row)

        self._edit.returnPressed.connect(self._ok_btn.click) # 回车等同【确认】

    def api_key_value(self) -> str:
        """返回输入框当前文本（未去除空白，交由调用方 strip 校验）。"""
        return self._edit.text()


def _persist_api_key(key: str) -> bool:
    """
    把密钥（自动去除首尾空白）覆盖写入唯一文件 asset_library/API-KEY.txt：
      - 文件名严格固定（绝不产生 API_KEY.txt 之类变体）；
      - 写入前判断文件是否存在 → 存在则直接覆盖（open 'w'），不新建副本；
      - 写入成功后删除旧版本误建的 API_KEY.txt，确保只剩一份密钥文件；
      - 全程打印统一路径调试日志，防止路径歧义导致重复文件。
    成功返回 True；失败返回 False（调用方弹窗提示）。
    """
    key = (key or "").strip()
    try:
        os.makedirs(ASSET_ROOT, exist_ok=True)
    except OSError as exc:
        print(f"[鲸鱼娘] 【警告】无法创建素材目录：{exc}")
        return False

    path = api_key_file_path()
    print(f"[鲸鱼娘] 【密钥写入】唯一密钥文件路径：{path}")   # 路径调试日志
    try:
        with open(path, "w", encoding="utf-8") as fh:   # 存在即直接覆盖，绝无副本
            fh.write(key + "\n")
    except OSError as exc:
        print(f"[鲸鱼娘] 【警告】无法写入密钥文件 {API_KEY_REL}（{exc}）")
        return False

    # 清理旧版本误建的变体文件，保证 asset_library 内只有 API-KEY.txt 一份
    try:
        legacy = legacy_key_file_path()
        if os.path.exists(legacy) and os.path.abspath(legacy) != os.path.abspath(path):
            os.remove(legacy)
            print(f"[鲸鱼娘] 【密钥写入】已清理旧版变体文件：{legacy}")
    except OSError as exc:
        print(f"[鲸鱼娘] 【警告】清理旧版密钥文件失败（{exc}）")
    return True


def ensure_api_key_at_startup() -> bool:
    """
    程序启动第一件事（必须处理完才能加载桌宠）：
      - asset_library/API-KEY.txt 已存在且有内容 → 正常读取密钥（自动去首尾空白/换行），
        【不执行 API 连通测试、不弹“注册成功”窗】，直接返回 True 正常启动桌宠；
        （若旧版 API_KEY.txt 变体存在，会自动迁移为唯一的 API-KEY.txt 并删除变体）
      - 不存在 / 内容为空（视为不存在）→ 模态输入对话框（场景A：首次新建密钥）：
          用户输入密钥点【确认】后【先测试、后写入】：
          · 连通测试成功 → 才把密钥写入 API-KEY.txt；弹出“注册成功！”3 秒自动关闭，
            返回 True（继续启动桌宠）；
          · 连通测试失败（网络异常/超时/密钥无效）→ 聊天框红字“API_KEY有误，
            请重新输入。”，【不写入 API-KEY.txt】，停留在输入弹窗供重新输入或退出；
          · 测试通过但写入磁盘失败（权限异常）→ 弹窗提示“写入磁盘失败”，返回 False，
            程序退出（磁盘不会产生 API-KEY.txt，内存密钥不生效）；
      - 用户点【退出程序】/ 输入为空 → 返回 False，直接退出，不生成任何密钥文件。
    说明：错误密钥永远不会写入磁盘——只有新输入密钥通过连通测试后才落盘保存；
    启动时已存在的密钥文件不再反复测试。
    """
    key = _read_existing_api_key_file()
    if key:
        # 场景“文件已存在”：不做连通测试、不弹窗，直接启动。
        # 顺手统一命名：若唯一文件 API-KEY.txt 缺失/为空，或旧版变体仍存在，则迁移清理。
        canonical_now = _read_key_from_file(api_key_file_path())
        if canonical_now != key or os.path.exists(legacy_key_file_path()):
            _persist_api_key(key)            # 覆盖写入唯一文件并删除旧版变体
        set_current_api_key(key)
        print("[鲸鱼娘] 【API密钥】检测到已存在的密钥文件，直接启动"
              "（跳过连通性测试）。")
        return True

    # ---- 场景 A：首次无密钥 → 输入弹窗；【先连通测试，通过后才写入文件】----
    while True:
        print("[鲸鱼娘] 【API密钥】未检测到有效密钥，弹出密钥设置对话框…")
        dlg = ApiKeySetupDialog()
        if dlg.exec() != QDialog.Accepted:     # 【退出程序】/ 关闭窗口
            print("[鲸鱼娘] 【API密钥】用户选择退出程序，桌宠不启动（不生成密钥文件）。")
            return False
        new_key = dlg.api_key_value().strip()  # 去除首尾空白/换行
        if not new_key:                        # 空内容点【确认】→ 直接退出
            print("[鲸鱼娘] 【API密钥】输入为空，按规则直接退出程序（不生成密钥文件）。")
            return False

        # ---- 第一步：先做连通性测试（子线程，不阻塞 UI；失败绝不写入）----
        print("[鲸鱼娘] 【API密钥】开始 DeepSeek 连通性测试（内容保密）…")
        if not run_connectivity_test_blocking(new_key):
            # ❌ 失败：聊天框红字提示 + 回到输入弹窗（磁盘上不会留下错误密钥）
            print("[鲸鱼娘] 【API密钥】连通性测试失败，不写入文件，重新要求输入密钥。")
            open_chat_for_key_error(None)
            continue

        # ✅ 测试通过 → 才把密钥写入唯一文件 API-KEY.txt
        print("[鲸鱼娘] 【API密钥】连通性测试成功，写入密钥文件…")
        if not _persist_api_key(new_key):
            QMessageBox.critical(
                None, "无法写入密钥文件",
                f"API 密钥测试通过，但写入磁盘失败（权限不足等）：\n"
                f"{os.path.join(ASSET_ROOT, API_KEY_REL)}\n"
                "程序即将退出（磁盘不会产生密钥文件，内存密钥不生效）。")
            print("[鲸鱼娘] 【API密钥】测试通过但写入磁盘失败，程序退出。")
            return False
        set_current_api_key(new_key)       # 写入成功后才生效（后续对话直接使用）
        hide_key_error_chat()              # 若之前弹出过错误聊天窗则隐藏
        show_auto_close_message("DeepSeek API", KEY_REGISTERED_TEXT)
        return True


class _KeyTestBridge(QObject):
    """工作线程 → 主线程 信号桥：API 连通性测试结果（bool）。"""
    result = Signal(bool)


def test_api_key_connectivity(api_key: str) -> bool:
    """
    轻量 DeepSeek 连通性测试：GET /models（仅校验密钥与网络连通，不做大模型对话）。
    网络异常 / 超时 / 非 200 一律视为连接失败（统一归类为失败）。
    本函数运行在工作线程中。
    """
    try:
        resp = requests.get(
            CONNECTIVITY_API_URL,
            headers={"Authorization": "Bearer " + (api_key or "").strip(),
                     "Accept": "application/json"},
            timeout=API_CONNECT_TIMEOUT_S,
        )
        return resp.status_code == 200
    except Exception as exc:  # noqa: BLE001 —— 无网络/超时/解析错误统一为失败
        print(f"[鲸鱼娘] 【API测试】连通性异常（{type(exc).__name__}）")
        return False


def _key_test_job(api_key: str, bridge: "_KeyTestBridge") -> None:
    """工作线程入口：执行连通性测试并把结果发回主线程。"""
    bridge.result.emit(test_api_key_connectivity(api_key))


_KEY_TEST_BRIDGES: list = []   # 强引用桥对象，防止工作线程迟到 emit 时桥已被回收


def run_connectivity_test_blocking(api_key: str) -> bool:
    """
    在工作线程中执行连通性测试并阻塞等待结果：
    内部事件循环驱动，UI 保持响应、绝不卡死；16 秒安全兜底防止无限等待。
    """
    loop = QEventLoop()
    bridge = _KeyTestBridge()
    _KEY_TEST_BRIDGES.append(bridge)          # 保活至结果到达后一段时间
    outcome: dict = {}

    def _on_result(ok: bool) -> None:
        outcome["ok"] = bool(ok)
        loop.quit()

    def _prune() -> None:
        try:
            _KEY_TEST_BRIDGES.remove(bridge)
        except ValueError:
            pass

    bridge.result.connect(_on_result)
    threading.Thread(target=_key_test_job, args=(api_key, bridge),
                     daemon=True).start()
    QTimer.singleShot(API_CONNECT_TIMEOUT_S * 1000 + 6000, loop.quit)  # 安全兜底
    QTimer.singleShot(4000, _prune)           # 结果早已到达后清理保活引用
    loop.exec()
    return bool(outcome.get("ok", False))


def show_auto_close_message(title: str, text: str, ms: int = 3000) -> None:
    """
    简易提示弹窗：模态、无按钮，显示 text，ms 毫秒后自动关闭（3 秒默认）。
    弹窗期间阻塞后续操作（模态）；定时器在弹窗事件循环中正常触发。
    """
    box = QDialog()
    box.setWindowTitle(title)
    box.setModal(True)
    box.setWindowModality(Qt.ApplicationModal)
    box.setMinimumWidth(260)
    box.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
    layout = QVBoxLayout(box)
    label = QLabel(text, box)
    label.setAlignment(Qt.AlignCenter)
    label.setStyleSheet("font-size:14px; color:#333333; padding:12px;")
    layout.addWidget(label)
    QTimer.singleShot(ms, box.accept)
    box.exec()
    box.deleteLater()


class ChangeApiKeyDialog(QDialog):
    """
    运行时【更改API-KEY】模态输入对话框：
      - 标题：修改DeepSeek API密钥；提示：本程序仅支持DeepSeek API。输入新Api Key；
      - 小字：密钥存放位置：程序目录/asset_library/API-KEY.txt；
      - 密码掩码、默认空白；按钮：确认 / 取消。
    点【确认】：空输入 → 红字提示留在弹窗；非空 →【先连通测试，通过后才覆盖写入
    API-KEY.txt】：成功 → 更新内存密钥并 accept()；失败 → 不覆盖原文件，
    聊天框红字提示并留在弹窗继续修改；测试通过但写盘失败 → 弹窗提示并退出程序。
    点【取消】：reject()（取消不会触碰原密钥文件）。
    """

    def __init__(self, owner_pet=None, parent=None):
        super().__init__(parent)
        self._pet = owner_pet               # 桌宠引用（失败时在其聊天窗输出红字）
        self._busy = False

        self.setWindowTitle("修改DeepSeek API密钥")
        self.setModal(True)
        self.setWindowModality(Qt.ApplicationModal)
        self.setMinimumWidth(460)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(10)

        tip = QLabel("本程序仅支持DeepSeek API。输入新Api Key", self)
        tip.setWordWrap(True)
        root.addWidget(tip)

        self._edit = QLineEdit(self)
        self._edit.setEchoMode(QLineEdit.Password)     # 掩码，不明文显示
        self._edit.setPlaceholderText("")
        root.addWidget(self._edit)

        self._error_label = QLabel("", self)
        self._error_label.setStyleSheet("color:#cc0000;")
        self._error_label.setWordWrap(True)
        self._error_label.setVisible(False)
        root.addWidget(self._error_label)

        hint = QLabel("密钥存放位置：程序目录/asset_library/API-KEY.txt", self)
        hint.setStyleSheet("color:#999999;")
        hint.setWordWrap(True)
        root.addWidget(hint)

        self._busy_label = QLabel("", self)
        self._busy_label.setStyleSheet("color:#888888;")
        self._busy_label.setVisible(False)
        root.addWidget(self._busy_label)

        row = QHBoxLayout()
        row.addStretch(1)
        self._ok_btn = QPushButton("确认", self)
        self._cancel_btn = QPushButton("取消", self)
        self._ok_btn.clicked.connect(self._on_confirm)
        self._cancel_btn.clicked.connect(self.reject)
        row.addWidget(self._ok_btn)
        row.addWidget(self._cancel_btn)
        root.addLayout(row)

        self._edit.returnPressed.connect(self._on_confirm)

    def api_key_value(self) -> str:
        return self._edit.text()

    def _set_busy(self, busy: bool, text: str = "") -> None:
        self._busy = busy
        self._ok_btn.setEnabled(not busy)
        self._cancel_btn.setEnabled(not busy)
        self._busy_label.setVisible(busy)
        if busy:
            self._busy_label.setText(text)
        self._edit.setEnabled(not busy)

    def _on_confirm(self) -> None:
        """【确认】：先对新密钥做连通测试，测试通过后才覆盖写入 API-KEY.txt。"""
        if self._busy:
            return
        key = self._edit.text().strip()      # 自动去除首尾空白/换行
        if not key:
            self._error_label.setText(KEY_EMPTY_HINT)   # 不能为空，留在弹窗
            self._error_label.setVisible(True)
            return
        self._error_label.setVisible(False)
        self._set_busy(True, "正在验证 DeepSeek API 密钥…")

        # 1) 【先测试】：子线程连通性测试（弹窗内事件循环，不冻结 UI）
        ok = run_connectivity_test_blocking(key)
        self._set_busy(False)
        if not ok:
            # ❌ 失败：不覆盖原有 API-KEY.txt；聊天框红字提示 + 保留弹窗继续修改
            open_chat_for_key_error(self._pet)
            self._error_label.setText(KEY_INVALID_TEXT)
            self._error_label.setVisible(True)
            return

        # 2) ✅ 测试通过 → 才覆盖写入唯一文件 API-KEY.txt
        if not _persist_api_key(key):
            QMessageBox.critical(
                self, "无法写入密钥文件",
                f"API 密钥测试通过，但写入磁盘失败（权限不足等）：\n"
                f"{os.path.join(ASSET_ROOT, API_KEY_REL)}\n"
                "程序即将退出（磁盘不会产生密钥文件，内存密钥不生效）。")
            self.reject()
            pet = self._pet
            if pet is not None:
                pet.quit_app()               # 结束整个程序
            else:
                app = QApplication.instance()
                if app is not None:
                    app.quit()
            return
        set_current_api_key(key)             # 更新内存密钥，后续对话直接用新密钥
        self.accept()


_QUOTE_PAIRS = (("“", "”"), ('"', '"'), ("‘", "’"))


def extract_line_text(raw: str):
    """从一行中取出引号内台词（兼容中文全角引号“ ”与英文引号）。"""
    s = raw.strip()
    if not s:
        return None
    for open_q, close_q in _QUOTE_PAIRS:
        if len(s) >= 2 and s.startswith(open_q) and s.endswith(close_q):
            inner = s[len(open_q):-len(close_q)].strip()
            return inner if inner else None
    m = re.search(r"[“‘\"]([^”’\"]+)[”’\"]", s)
    if m:
        inner = m.group(1).strip()
        return inner if inner else None
    return s


def load_talk_pool(rel_path: str, fallback: list) -> list:
    """
    读取台词池：txt 每行一条“台词文本”，忽略空行；返回引号内文本列表。
    文件不存在 / 为空 / 读取异常 → 返回内置兜底台词，程序不崩溃。
    """
    path = os.path.join(ASSET_ROOT, rel_path)
    pool: list = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8-sig") as fh:
                for raw in fh:
                    text = extract_line_text(raw)
                    if text:
                        pool.append(text)
        except OSError as exc:
            print(f"[鲸鱼娘] 【警告】台词文件读取异常，改用内置兜底台词：{exc}")
            pool = []
    else:
        print(f"[鲸鱼娘] 【警告】台词文件不存在，改用内置兜底台词：{path}")
    if not pool:
        pool = list(fallback)
    return pool


def wrap_text(text: str, font: QFont, max_width: int) -> list:
    """按像素宽度逐字符折行（兼容中英文混排），返回行列表。"""
    fm = QFontMetrics(font)
    if not text:
        return [""]
    lines: list = []
    for paragraph in text.splitlines():
        if not paragraph:
            lines.append("")
            continue
        line = ""
        for ch in paragraph:
            trial = line + ch
            if fm.horizontalAdvance(trial) > max_width and line:
                lines.append(line)
                line = ch
            else:
                line = trial
        if line:
            lines.append(line)
    return lines if lines else [""]


# ================================================================================
# 二·五、RAG 知识库工具（目录 / 文档提取 / 上限截断 / 资源管理器窗口检测）
# ================================================================================

def ensure_rag_dir() -> str:
    """RAG 文件夹不存在则自动创建（程序启动即调用，幂等）。"""
    try:
        os.makedirs(RAG_DIR, exist_ok=True)
    except OSError as exc:
        print(f"[鲸鱼娘] 【警告】创建 RAG 文件夹失败：{exc}")
    return RAG_DIR


def is_supported_document(path: str) -> bool:
    """仅支持 .txt / .docx，不支持旧版 .doc 二进制文件。"""
    return os.path.splitext(path)[1].lower() in SUPPORTED_EXT


def count_rag_documents() -> int:
    """实时统计 RAG 文件夹内 .txt + .docx 文件总数（异常返回 0，不崩溃）。"""
    try:
        if not os.path.isdir(RAG_DIR):
            return 0
        return sum(1 for name in os.listdir(RAG_DIR)
                   if os.path.isfile(os.path.join(RAG_DIR, name))
                   and is_supported_document(name))
    except OSError as exc:
        print(f"[鲸鱼娘] 【警告】统计 RAG 文档数失败：{exc}")
        return 0


def _read_txt_text(path: str) -> str:
    """读取 .txt 纯文本（utf-8 → gb18030 兜底，尽量不乱码）。"""
    with open(path, "rb") as fh:
        raw = fh.read()
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def extract_docx_text(path: str) -> str:
    """提取 .docx 纯文本（zip + 解析 word/document.xml；损坏/异常抛出由调用方容错）。"""
    with zipfile.ZipFile(path) as zf:
        if "word/document.xml" not in zf.namelist():
            raise ValueError("docx 缺少 word/document.xml")
        data = zf.read("word/document.xml")
    root = ET.fromstring(data)
    lines = []
    for para in root.iter(_W_NS + "p"):
        text = "".join(t.text or "" for t in para.iter(_W_NS + "t")).strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


def extract_document_text(path: str) -> str:
    """按后缀提取纯文本：txt / docx；其余类型抛 ValueError。"""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt":
        return _read_txt_text(path)
    if ext == ".docx":
        return extract_docx_text(path)
    raise ValueError(f"不支持的文档格式：{path}")


def load_rag_text() -> dict:
    """
    读取 RAG 文件夹全部 .txt/.docx 的纯文本并做开销保护：
      - 单文档 > RAG_MAX_DOC(8000) 自动截断；
      - 合并总文本 > RAG_MAX_TOTAL(20000) 截断并置 combined_truncated。
    损坏文档自动跳过并控制台警告，绝不崩溃。
    返回 dict：text / loaded / combined_truncated / doc_truncated / skipped。
    """
    # 逐篇累积到总上限，而不是先把所有文档拼成一个大字符串再截断；这样资料
    # 较多时峰值内存保持在实际会发送给模型的文本量附近。
    docs: list = []
    skipped = 0
    doc_truncated = False
    combined_truncated = False
    remaining = RAG_MAX_TOTAL
    if os.path.isdir(RAG_DIR):
        try:
            names = sorted(os.listdir(RAG_DIR))
        except OSError as exc:
            print(f"[鲸鱼娘] 【警告】读取 RAG 目录失败：{exc}")
            names = []
        for name in names:
            path = os.path.join(RAG_DIR, name)
            if not (os.path.isfile(path) and is_supported_document(name)):
                continue
            try:
                text = extract_document_text(path).strip()
            except Exception as exc:  # noqa: BLE001 —— 损坏文档自动跳过
                print(f"[鲸鱼娘] 【警告】文档损坏已跳过：{path}（{type(exc).__name__}）")
                skipped += 1
                continue
            if not text:
                continue
            if len(text) > RAG_MAX_DOC:          # 单文档上限 8000
                text = text[:RAG_MAX_DOC]
                doc_truncated = True
            separator_len = 2 if docs else 0
            text_capacity = remaining - separator_len
            if text_capacity <= 0:
                combined_truncated = True
                break
            if len(text) > text_capacity:
                text = text[:text_capacity]
                combined_truncated = True
            docs.append(text)
            remaining -= separator_len + len(text)
            if remaining <= 0:
                break
    merged = "\n\n".join(docs)
    return {
        "text": merged,
        "loaded": len(merged),
        "combined_truncated": combined_truncated,
        "doc_truncated": doc_truncated,
        "skipped": skipped,
    }


# ---- 资源管理器窗口检测（Windows）----

def _enumerate_window_titles() -> list:
    """枚举所有可见顶层窗口标题（仅 Windows；异常返回空表，不崩溃）。"""
    titles: list = []
    try:
        user32 = ctypes.windll.user32
    except Exception:  # noqa: BLE001 —— 非 Windows 平台
        return titles
    try:
        proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool,
                                       ctypes.c_void_p, ctypes.c_void_p)

        def _cb(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            text = buf.value.strip()
            if text:
                titles.append(text)
            return True

        user32.EnumWindows(proc_type(_cb), 0)
    except Exception as exc:  # noqa: BLE001
        print(f"[鲸鱼娘] 【警告】枚举窗口标题失败：{exc}")
    return titles


def find_folder_window(path: str) -> bool:
    """按标题查找资源管理器窗口（标题=文件夹名或完整路径）；找不到返回 False。"""
    try:
        norm = os.path.normpath(path).lower()
        base = os.path.basename(norm)
        for title in _enumerate_window_titles():
            low = title.lower()
            if low == base or low == norm:
                return True
            if low.startswith(base + " - "):      # 形如 “RAG - 文件资源管理器”
                return True
    except Exception as exc:  # noqa: BLE001
        print(f"[鲸鱼娘] 【警告】查找文件夹窗口失败：{exc}")
    return False


def open_folder_in_explorer(path: str) -> bool:
    """调用系统资源管理器打开 RAG 文件夹窗口；失败返回 False（不抛异常）。"""
    try:
        if sys.platform == "win32":
            os.startfile(path)                    # noqa: S606 —— Windows 原生
            return True
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"[鲸鱼娘] 【警告】打开资源管理器失败：{exc}")
        return False


# ================================================================================
# 二·七、config.json（窗口位置记忆）与红色【退出】菜单项工具
# ================================================================================

def load_window_position():
    """
    读取 config.json（{window_x, window_y}，int）。
    文件不存在 / 损坏 / 字段缺失 / 类型错误 / 权限不足 → 返回 None（使用默认右下角）。
    """
    try:
        if not os.path.exists(CONFIG_PATH):
            return None
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        x = int(data["window_x"])
        y = int(data["window_y"])
        return x, y
    except Exception as exc:  # noqa: BLE001 —— 损坏/缺失/权限异常一律回退默认位置
        print(f"[鲸鱼娘] 【警告】config.json 读取失败，使用默认右下角位置（{exc}）")
        return None


def save_window_position(x: int, y: int) -> bool:
    """把窗口坐标写入 config.json（覆盖式，运行时生成；异常捕获不崩溃）。"""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump({"window_x": int(x), "window_y": int(y)}, fh,
                      ensure_ascii=False, indent=2)
        print(f"[鲸鱼娘] 【位置保存】config.json <- ({int(x)}, {int(y)})")
        return True
    except Exception as exc:  # noqa: BLE001 —— 权限不足等只警告
        print(f"[鲸鱼娘] 【警告】config.json 写入失败：{exc}")
        return False


def clamp_position_to_screen(x: int, y: int, w: int, h: int):
    """
    坐标有效性兜底：把 (x,y) 钳制到主屏可用区域内（至少保留 60px 可见），
    防止 config.json 里的旧坐标把桌宠带到屏幕外再也找不到。
    """
    screen = QApplication.primaryScreen()
    if screen is None:
        return int(x), int(y)
    geo = screen.availableGeometry()
    nx = max(geo.left() - w + 60, min(int(x), geo.right() - 60))
    ny = max(geo.top(), min(int(y), geo.bottom() - 60))
    return nx, ny


class _RedQuitLabel(QLabel):
    """红色【退出】菜单项内容：点击即触发所属 action。"""

    def __init__(self, action, parent=None):
        super().__init__("退出", parent)
        self._action = action
        self.setStyleSheet("color:#e00000; background:transparent;"
                           "padding:5px 26px 5px 24px;")
        self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._action.trigger()
        super().mouseReleaseEvent(event)


class RedQuitAction(QWidgetAction):
    """红色字体【退出】菜单项：在 QMenu 中由 createWidget 生成红字内容。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("退出")

    def createWidget(self, parent):  # noqa: N802 —— QMenu 需要
        return _RedQuitLabel(self, parent)


def make_red_quit_action(menu: QMenu, slot):
    """构造红色字体的【退出】菜单项并绑定点击回调。"""
    act = RedQuitAction(menu)
    act.triggered.connect(slot)
    return act


# ================================================================================
# 二、对话气泡（固定 3 秒 / 单例 / 跟随桌宠）
# ================================================================================

class SpeechBubble(QWidget):
    """白色半透明圆角气泡 + 底部小三角，显示在桌宠上方；由气泡计时器 3 秒后关闭。"""

    def __init__(self, text: str):
        super().__init__(None)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self._text = text if text else "……"
        self._font = QFont("Microsoft YaHei", 11)
        self._font.setStyleStrategy(QFont.PreferAntialias)
        self.setFont(self._font)
        self._fm = QFontMetrics(self._font)

        self._pad_x, self._pad_y = 16, 12
        self._tail_h, self._radius = 10, 14

        max_text_w = 260
        self._lines = wrap_text(self._text, self._font, max_text_w)
        line_w = max((self._fm.horizontalAdvance(line) for line in self._lines),
                     default=0)
        line_h = self._fm.lineSpacing()
        w = max(line_w + self._pad_x * 2, 70)
        h = line_h * len(self._lines) + self._pad_y * 2 + self._tail_h
        self.resize(int(w), int(h))

    def place_above(self, owner: QWidget) -> None:
        """放到宠物窗口正上方（顶部放不下则放下方），并做屏幕边界钳制。"""
        screen = owner.screen() if owner.screen() else QApplication.primaryScreen()
        pet = owner.frameGeometry()
        x = pet.center().x() - self.width() // 2
        y = pet.top() - self.height() - 8
        if screen is None:
            self.move(int(x), int(y))
            return
        geo = screen.availableGeometry()
        if y < geo.top():
            y = pet.bottom() + 8
        x = max(geo.left() + 2, min(x, geo.right() - self.width() - 2))
        self.move(int(x), int(y))

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        body = QRectF(1.5, 1.5, w - 3, h - self._tail_h - 3)
        radius, tail_h = self._radius, self._tail_h

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 28))
        painter.drawRoundedRect(body.translated(0, 3), radius, radius)

        painter.setPen(QPen(QColor(110, 110, 110, 90), 1.5))
        painter.setBrush(QColor(255, 255, 255, 240))
        painter.drawRoundedRect(body, radius, radius)

        cx = int(w // 2)
        bottom = int(body.bottom())
        triangle = QPolygon([QPoint(cx - 9, bottom), QPoint(cx + 9, bottom),
                             QPoint(cx, bottom + tail_h - 1)])
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 240))
        painter.drawPolygon(triangle)

        painter.setFont(self._font)
        painter.setPen(QColor(50, 50, 50))
        line_h = self._fm.lineSpacing()
        top = body.top() + self._pad_y
        for i, line in enumerate(self._lines):
            line_x = (w - self._fm.horizontalAdvance(line)) / 2.0
            baseline_y = top + i * line_h + self._fm.ascent()
            painter.drawText(QPointF(line_x, baseline_y), line)
        painter.end()


# ================================================================================
# 三、余额查询（本地 requests + 独立线程，主程序内部完成，绝不调用外部脚本）
# ================================================================================

class BalanceBridge(QObject):
    """线程 → 主线程 信号桥：余额查询结果（序号 + 展示文本）回传 UI。"""
    result = Signal(int, str)


def request_balance_text(api_key: str) -> str:
    """
    本地调用 DeepSeek 官方 /user/balance（GET，超时 10 秒）。
    成功 → “目前APIKEY剩余：¥ xx.xx元。”；任何异常/非 200 → 失败文案。
    本函数运行在工作线程中，绝不阻塞 Qt 界面。
    """
    try:
        resp = requests.get(
            BALANCE_API_URL,
            headers={"Authorization": "Bearer " + api_key.strip(),
                     "Accept": "application/json"},
            timeout=BALANCE_TIMEOUT_S,
        )
        if resp.status_code != 200:
            print(f"[鲸鱼娘] 【余额查询失败】HTTP {resp.status_code}")
            return BALANCE_FAIL_TEXT
        try:
            data = resp.json()
        except ValueError:
            print("[鲸鱼娘] 【余额查询失败】响应不是合法 JSON")
            return BALANCE_FAIL_TEXT
        infos = (data or {}).get("balance_infos") or []
        if not infos:
            print("[鲸鱼娘] 【余额查询失败】响应中没有 balance_infos 字段")
            return BALANCE_FAIL_TEXT
        total = 0.0
        for info in infos:
            try:
                total += float(str(info.get("total_balance", "0")))
            except (TypeError, ValueError):
                continue
        return BALANCE_OK_TEXT.format(amount=total)
    except Exception as exc:  # noqa: BLE001 —— 网络异常/超时/密钥无效等统一失败
        print(f"[鲸鱼娘] 【余额查询异常】{type(exc).__name__}: {exc}")
        return BALANCE_FAIL_TEXT


# ================================================================================
# 四、聊天子窗口（右键菜单【聊聊天】弹出；异步 DeepSeek；关窗仅隐藏）
# ================================================================================

class ChatWindow(QWidget):
    """
    与鲸鱼娘聊天的独立子窗口：
      - 上方对话历史 + 下方输入框（回车 / 点【发送】）；
      - QNetworkAccessManager 异步请求，不阻塞桌宠；
      - API Key 每次发送前从 asset_library/API_KEY.txt 读取（缺失/出错展示在窗内）；
      - 关闭窗口只隐藏，不退出桌宠本体。
    """

    def __init__(self, pet=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("与鲸鱼娘聊天")
        self.resize(420, 560)
        self.setMinimumSize(340, 420)

        self._pet = pet            # 桌宠引用：读取 RAG 知识库 / 更新小字提示
        self._history: list = []
        self._busy: bool = False
        self._nam = QNetworkAccessManager(self)
        self._reply = None

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        self._view = QTextEdit(self)
        self._view.setReadOnly(True)
        self._view.setAcceptRichText(True)
        self._view.setFont(QFont("Microsoft YaHei", 10))
        root.addWidget(self._view, 1)

        input_row = QHBoxLayout()
        input_row.setSpacing(6)
        self._edit = QLineEdit(self)
        self._edit.setPlaceholderText("输入你的问题，回车或点【发送】…")
        self._edit.setFont(QFont("Microsoft YaHei", 10))
        input_row.addWidget(self._edit, 1)
        self._send_btn = QPushButton("发送", self)
        self._send_btn.setMinimumWidth(72)
        input_row.addWidget(self._send_btn)
        root.addLayout(input_row)

        self._status = QLabel("就绪：右键桌宠 → 聊聊天 即可唤出本窗口。", self)
        self._status.setStyleSheet("color:#888888;")
        root.addWidget(self._status)

        # RAG 小字提示：已加载RAG文本：X / 20000字（超出上限额外提示已截断）
        self._rag_label = QLabel(self)
        self._rag_label.setStyleSheet("color:#a0a0a0;")
        self._rag_label.setWordWrap(True)
        root.addWidget(self._rag_label)
        if pet is not None:
            pet.refresh_rag()          # 打开聊天窗口即刷新知识库
        self.update_rag_label()

        self._edit.returnPressed.connect(self._on_send)
        self._send_btn.clicked.connect(self._on_send)
        self._append_view('<span style="color:#666666;">—— 与鲸鱼娘对话 ——<br>'
                          '直接输入问题按回车即可。</span>')
        self._edit.setFocus()

    # ---------------- 内部工具 ----------------

    def update_rag_label(self) -> None:
        """刷新底部小字：已加载RAG文本：X / 20000字（超长自动截断时附加提示）。"""
        loaded = 0
        truncated = False
        pet = self._pet
        if pet is not None:
            loaded = getattr(pet, "rag_loaded", 0) or 0
            truncated = bool(getattr(pet, "rag_combined_truncated", False))
        text = RAG_LABEL_TEXT.format(loaded=loaded, max=RAG_MAX_TOTAL)
        if truncated:
            text += "（内容过长已截断）"
        self._rag_label.setText(text)

    def _append_view(self, html_fragment: str) -> None:
        self._view.append(html_fragment)
        bar = self._view.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._edit.setEnabled(not busy)
        self._send_btn.setEnabled(not busy)
        self._send_btn.setText("等待中…" if busy else "发送")
        self._status.setText("鲸鱼娘思考中…（异步请求，不阻塞桌宠）" if busy else "就绪。")

    # ---------------- 发送流程 ----------------

    def _on_send(self) -> None:
        if self._busy:
            return
        text = self._edit.text().strip()
        if not text:
            return
        self._append_view(f'<b style="color:#1a6fb5;">你：</b>'
                          f'<span style="color:#222222;">{_html(text)}</span>')
        self._edit.clear()
        self._set_busy(True)

        api_key = read_api_key()   # 从 asset_library/API-KEY.txt 读取
        if not api_key:
            self._append_view('<span style="color:#cc0000;">【错误】缺少 DeepSeek '
                              'API Key：未找到 asset_library/API-KEY.txt。</span>')
            self._set_busy(False)
            return
        self._history.append({"role": "user", "content": text})
        self._request_chat(api_key)

    def _build_chat_messages(self) -> list:
        """
        组装发给模型的 messages：
          system 人设 →（历史对话）→【参考知识库文档】区块 → 当前用户问题。
        知识库无有效内容时不插入区块（不额外消耗 token）。
        system 内置规则：优先参考知识库事实回答、无相关内容用自身知识、
        禁止大段复制原文、保持傲娇人设、禁止“根据文档”等机械话术。
        """
        persona = ("你是桌宠“鲸鱼娘”，一只聪明又慵懒、傲娇带甜、自称鲸鱼娘的"
                   "二次元少女，始终服从主人；只使用简体中文，简短自然地聊天；"
                   "不要提及自己是 AI 或模型。\n"
                   "【知识库回答规则】优先参考【参考知识库文档】中的事实来回答用户；"
                   "若文档中没有相关内容，则使用你自己的知识回答；"
                   "禁止大段复制文档原文，回答始终保留鲸鱼娘傲娇人设；"
                   "禁止出现“根据文档”“根据资料”之类的机械话术。")
        messages: list = [{"role": "system", "content": persona}]
        # 限制上下文，避免长时间聊天导致请求体、费用与响应延迟持续增长。
        # 末尾一条始终是本轮用户问题，因此不会被截掉。
        history = self._history[-CHAT_HISTORY_MAX_MESSAGES:]
        rag_text = ""
        if self._pet is not None:
            rag_text = getattr(self._pet, "rag_text", "") or ""
        rag_block = None
        if rag_text.strip():
            rag_block = {"role": "system",
                         "content": "【参考知识库文档】\n" + rag_text}
        if history:
            past, current = history[:-1], history[-1]
            messages += past
            if rag_block is not None:          # system 之后、用户问题之前
                messages.append(rag_block)
            messages.append(current)
        else:
            if rag_block is not None:
                messages.append(rag_block)
        return messages

    def _request_chat(self, api_key: str) -> None:
        messages = self._build_chat_messages()
        payload = {"model": DEEPSEEK_MODEL, "messages": messages, "stream": False}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        request = QNetworkRequest(QUrl(CHAT_API_URL))
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        request.setRawHeader(b"Authorization", b"Bearer " + api_key.encode("utf-8"))
        request.setTransferTimeout(CHAT_TIMEOUT_MS)

        reply = self._nam.post(request, body)
        self._reply = reply
        reply.finished.connect(self._on_reply_finished)

    def _on_reply_finished(self) -> None:
        reply = self._reply
        self._reply = None
        if reply is None:
            self._set_busy(False)
            return
        reply.deleteLater()
        raw = bytes(reply.readAll()).decode("utf-8", errors="replace")
        http_status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        try:
            data = json.loads(raw) if raw else {}
        except ValueError:
            data = {}
        if reply.error() != QNetworkReply.NoError or (http_status and http_status != 200):
            server_msg = (data.get("error") or {}).get("message") if isinstance(data, dict) else None
            error_text = (f"HTTP {http_status}：{server_msg}" if server_msg
                          else f"HTTP {http_status} / {reply.errorString()}")
            self._append_view('<span style="color:#cc0000;">【错误】'
                              + _html(error_text) + '</span>')
            self._set_busy(False)
            return
        try:
            content = ((data.get("choices") or [{}])[0]
                       .get("message", {}).get("content", ""))
        except (AttributeError, IndexError):
            content = ""
        if not content:
            self._append_view('<span style="color:#cc0000;">【错误】DeepSeek 返回了'
                              '空内容。</span>')
            self._set_busy(False)
            return
        self._append_view(f'<b style="color:#0a7a3d;">鲸鱼娘：</b>'
                          f'<span style="color:#222222;">{_html(content)}</span>')
        self._history.append({"role": "assistant", "content": content})
        self._set_busy(False)

    # ---------------- 窗口行为 ----------------

    def append_api_key_error(self) -> None:
        """以红色字体在聊天历史输出 API 密钥错误提示（不影响对话历史）。"""
        self._append_view(f'<span style="color:#cc0000;font-weight:bold;">'
                          f'{KEY_INVALID_TEXT}</span>')

    def show_and_activate(self, anchor: QRect = None) -> None:
        """显示聊天窗（anchor 为空时居中于主屏；anchor 非空则就近放其右侧）。"""
        if not self.isVisible():
            screen = QApplication.primaryScreen()
            geo = screen.availableGeometry() if screen else None
            if anchor is None and geo is not None:
                x = geo.center().x() - self.width() // 2
                y = geo.center().y() - self.height() // 2
            elif anchor is not None:
                x, y = anchor.right() + 16, anchor.top()
                if geo is not None:
                    if x + self.width() > geo.right():
                        x = geo.center().x() - self.width() // 2
                    if y < geo.top():
                        y = geo.top() + 40
                    if y + self.height() > geo.bottom():
                        y = geo.center().y() - self.height() // 2
            else:
                x, y = 0, 0
            self.move(int(x), int(y))
        self.show()
        self.raise_()
        self.activateWindow()
        self._edit.setFocus()

    def closeEvent(self, event) -> None:  # noqa: N802 —— 用户关窗只隐藏；程序退出时才真正关闭
        pet = self._pet
        if pet is not None and getattr(pet, "_quitting", False):
            event.accept()          # 完整退出流程中：允许窗口真正关闭
            return
        event.ignore()
        self.hide()


# ---- API 密钥错误提示聊天窗（启动阶段尚未有桌宠时使用；运行期优先用桌宠聊天窗）----

_KEY_ERROR_CHAT = None      # type: "ChatWindow" | None


def _ensure_key_error_chat() -> "ChatWindow":
    """懒创建独立的“密钥错误提示”聊天窗（pet=None 的普通聊天窗）。"""
    global _KEY_ERROR_CHAT
    if _KEY_ERROR_CHAT is None:
        _KEY_ERROR_CHAT = ChatWindow(pet=None)
        app = QApplication.instance()
        if app is not None:
            app._key_error_chat = _KEY_ERROR_CHAT      # 强引用，防被回收
    return _KEY_ERROR_CHAT


def open_chat_for_key_error(owner_pet=None) -> "ChatWindow":
    """
    API 连通性测试失败提示：优先输出到桌宠的聊天窗（没有则新建），
    聊天框以红色文字显示：API_KEY有误，请重新输入。
    """
    chat = None
    if owner_pet is not None:
        if getattr(owner_pet, "_chat_window", None) is None:
            owner_pet.open_chat_window()
        chat = owner_pet._chat_window
    if chat is None:
        chat = _ensure_key_error_chat()
    chat.append_api_key_error()
    if owner_pet is not None:
        chat.show_and_activate(owner_pet.frameGeometry())
    else:
        chat.show_and_activate(None)
    print("[鲸鱼娘] 【API密钥】聊天框已输出红色提示：", KEY_INVALID_TEXT)
    return chat


def hide_key_error_chat() -> None:
    """隐藏启动阶段使用的错误提示聊天窗（启动成功后调用，避免残留窗口）。"""
    global _KEY_ERROR_CHAT
    if _KEY_ERROR_CHAT is not None:
        _KEY_ERROR_CHAT.hide()


def _html(text: str) -> str:
    """极简 HTML 转义（聊天窗内使用）。"""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


# ================================================================================
# 四·五、系统托盘（Windows 右下角隐藏图标）
# ================================================================================

def make_tray_icon() -> QIcon:
    """
    托盘图标：优先使用桌宠自身素材 nothing.png（程序自身图标）；
    素材缺失/损坏时回退到程序化绘制的“鲸”字蓝圆标，保证不崩溃。
    """
    path = os.path.join(ASSET_ROOT, IMAGE_RELS["nothing"])
    pm = QPixmap(path)
    if not pm.isNull():
        return QIcon(pm)

    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(52, 160, 235))
    painter.drawEllipse(2, 2, 60, 60)
    font = QFont("Microsoft YaHei", 30)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor(255, 255, 255))
    painter.drawText(QRectF(0, 2, 64, 60), Qt.AlignCenter, "鲸")
    painter.end()
    return QIcon(pm)


class PetTrayIcon(QSystemTrayIcon):
    """
    Windows 右下角系统托盘（程序启动即注册，常驻后台，出现在隐藏图标列表）：
      - 右键菜单与桌宠本体右键菜单一致：【聊聊天】【查询余额】【退出】；
      - 双击托盘图标 → 显示/还原被隐藏的桌宠主窗口；
      - 仅【退出】执行完整退出流程（aboutToQuit → pet._cleanup 统一清理）。
    """

    def __init__(self, pet: "DesktopPet"):
        super().__init__(pet)
        self._pet = pet
        self.setIcon(make_tray_icon())          # 程序自身图标
        self.setToolTip("鲸鱼娘桌宠\n（右键：聊聊天/查询余额/添加资料/查看资料/"
                        "更改API-KEY/重置位置/隐藏鲸鱼娘/退出；双击还原窗口）")

        # 右键菜单与桌宠右键菜单保持一致（顺序严格一致，含分隔线与红色【退出】）
        # QSystemTrayIcon 非 QWidget，菜单不设其父，仅用 self._menu 强引用保活
        menu = QMenu()
        act_chat = QAction("聊聊天", menu)
        act_balance = QAction("查询余额", menu)
        act_add = QAction("添加资料文件", menu)
        act_view = QAction("查看已有资料", menu)
        act_key = QAction("更改API-KEY", menu)
        act_reset = QAction("重置位置", menu)
        self._hide_act = QAction("隐藏鲸鱼娘", menu)   # 文本按显示/隐藏状态动态切换
        act_chat.triggered.connect(pet.open_chat_window)
        act_balance.triggered.connect(pet.start_query)
        act_add.triggered.connect(pet.start_add_documents)
        act_view.triggered.connect(pet.start_view_files)
        act_key.triggered.connect(pet.change_api_key)
        act_reset.triggered.connect(pet.reset_position)
        self._hide_act.triggered.connect(pet.toggle_hide_whale)
        for act in (act_chat, act_balance, act_add, act_view, act_key, act_reset):
            menu.addAction(act)
        menu.addSeparator()                       # 「重置位置」与「隐藏鲸鱼娘」之间的分隔线
        menu.addAction(self._hide_act)
        menu.addAction(make_red_quit_action(menu, pet.quit_app))   # 红色【退出】
        menu.aboutToShow.connect(self._sync_menu_labels)
        self.setContextMenu(menu)
        self._menu = menu                        # 强引用保活

        self.activated.connect(self._on_activated)
        self.show()

    def _sync_menu_labels(self) -> None:
        """弹出托盘菜单前同步【隐藏/显示鲸鱼娘】文案。"""
        self._hide_act.setText("显示鲸鱼娘" if self._pet.isHidden()
                               else "隐藏鲸鱼娘")

    def _on_activated(self, reason) -> None:  # noqa: N802
        """双击托盘图标：恢复显示桌宠并弹固定气泡“我鲸鱼娘又回来了！”。"""
        if reason == QSystemTrayIcon.DoubleClick:
            pet = self._pet
            if pet.isHidden():
                pet.show_whale(greet=True)
            else:
                pet.raise_()
                pet.activateWindow()


# ================================================================================
# 五、桌宠主窗口（状态机核心）
# ================================================================================

class DesktopPet(QWidget):
    """
    桌宠窗口：无边框 + 背景透明 + 置顶 Tool。
    状态机：idle(nothing/eat/think) / touch / pickup(拖拽) / query(余额) /
           file_import(资料导入反馈) / view_files(查看资料)。
    优先级：pickup > touch > query > file_import > view_files > idle；
    高优先级打断/暂停低优先级，结束后回到 idle 并接续之前计时进度
    （不重置 5 分钟周期）。
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("鲸鱼娘桌宠")
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        # ---------------- 图片动态加载（不缓存 QPixmap，每次状态切换现读磁盘） ----------------
        self._cur_key: str = "nothing"
        self._pixmap: QPixmap | None = None

        # ---------------- 系统托盘 / 隐藏状态 ----------------
        self._tray = None           # 由 main() 注册的 QSystemTrayIcon（不支持则为 None）
        self._hidden = False        # 主窗口被隐藏（驻留托盘）期间暂停待机计时
        self._quitting = False      # 完整退出中：允许窗口真正关闭，避免关闭事件阻断退出

        # ---------------- 状态机 ----------------
        self._state: str = "idle"            # idle / touch / pickup / query
        self._stage_idx: int = 0             # idle 阶段下标（IDLE_ORDER）
        self._stage_remaining: int = IDLE_MS["nothing"]   # 当前阶段剩余毫秒
        self._idle_paused: bool = False      # 被高优先级状态暂停

        # ---------------- 鼠标交互状态 ----------------
        self._pressing = False
        self._drag_active = False            # 是否已判定为拖拽
        self._press_global = QPoint()
        self._drag_offset = None
        self._suppress_next_release = False  # 双击第二下释放（消费掉）
        self._query_seq = 0                  # 余额查询序号（丢弃过期结果）

        # ---------------- RAG 文档管理 ----------------
        self.rag_text: str = ""                       # 已加载知识库纯文本（聊天注入用）
        self.rag_loaded: int = 0                      # 已加载字数（截断后）
        self.rag_combined_truncated: bool = False     # 合并总文本是否超限截断
        self.rag_doc_truncated: bool = False          # 是否存在单文档超长截断
        self._view_open = False                       # view_files：资源管理器窗口已出现
        self._view_poll_count = 0                     # 等待窗口出现的轮询计数
        ensure_rag_dir()                              # 启动即检测/创建 RAG 文件夹
        self.setAcceptDrops(True)                     # 允许外部文件拖拽导入（与 PickUp 互不干扰）

        # ---------------- 弹窗 / 聊天 ----------------
        self._bubble: SpeechBubble | None = None
        self._chat_window: ChatWindow | None = None
        self._balance_bridge = BalanceBridge(self)
        self._balance_bridge.result.connect(self._on_balance_result)

        # ---------------- 计时器（全部由 _cleanup 统一停止） ----------------
        self._stage_timer = QTimer(self)     # idle 阶段倒计时（单发）
        self._stage_timer.setSingleShot(True)
        self._stage_timer.setTimerType(Qt.PreciseTimer)
        self._stage_timer.timeout.connect(self._on_stage_timeout)

        self._nothing_timer = QTimer(self)   # nothing 阶段 30s 待机台词
        self._nothing_timer.setInterval(IDLE_TALK_MS)
        self._nothing_timer.setTimerType(Qt.PreciseTimer)
        self._nothing_timer.timeout.connect(self._pop_nothing_line)

        self._touch_timer = QTimer(self)     # touch 3 秒倒计时（单发）
        self._touch_timer.setSingleShot(True)
        self._touch_timer.setInterval(TOUCH_MS)
        self._touch_timer.timeout.connect(self._on_touch_timeout)

        self._bubble_timer = QTimer(self)    # 气泡 3 秒自动销毁（单发）
        self._bubble_timer.setSingleShot(True)
        self._bubble_timer.setInterval(BUBBLE_MS)
        self._bubble_timer.timeout.connect(self._kill_bubble)

        self._click_timer = QTimer(self)     # 单击/双击判定延迟（单发）
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._do_touch)

        self._file_import_timer = QTimer(self)   # file_import 反馈 3 秒（单发）
        self._file_import_timer.setSingleShot(True)
        self._file_import_timer.setInterval(FILE_IMPORT_MS)
        self._file_import_timer.timeout.connect(self._on_file_import_timeout)

        self._shake_timer = QTimer(self)     # 导入失败窗口抖动（重复触发）
        self._shake_timer.setInterval(SHAKE_STEP_MS)
        self._shake_timer.timeout.connect(self._on_shake_tick)
        self._shake_base = QPoint()          # 抖动起始位置
        self._shake_tick = 0                 # 抖动步数
        self._shake_active = False           # 是否正在抖动

        self._view_timer = QTimer(self)      # view_files：轮询监听资源管理器窗口关闭
        self._view_timer.setInterval(VIEW_POLL_MS)
        self._view_timer.timeout.connect(self._on_view_poll)

        self._cheerup_timer = QTimer(self)   # cheerup_show 登场状态 3 秒（单发）
        self._cheerup_timer.setSingleShot(True)
        self._cheerup_timer.setInterval(CHEERUP_MS)
        self._cheerup_timer.timeout.connect(self._on_cheerup_timeout)

        # ---------------- 登场 / 待机启动控制 ----------------
        # 待机计时器严禁提前启动：cheerup_show 3 秒结束后（或素材缺失直接跳过）才开启。
        self._idle_started = False    # idle 状态机计时是否已启动
        self._set_image("nothing")    # 仅先确定窗口尺寸，不启动任何待机计时
        # 初始定位（config.json 覆盖逻辑在 main() 中处理）
        self._home_rect = self._compute_center_geometry()

    # ================= 素材加载 =================

    def _make_blank_placeholder(self, key: str) -> QPixmap:
        """素材缺失/损坏时的空白占位（半透明淡色块 + 细边框，保证可点击不崩溃）。"""
        w, h = 240, 300
        pm = QPixmap(w, h)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(120, 140, 170, 120), 2))
        p.setBrush(QColor(205, 220, 240, 90))
        p.drawRoundedRect(QRectF(2, 2, w - 4, h - 4), 12, 12)
        p.end()
        return pm

    def _load_state_pixmap(self, key: str) -> QPixmap:
        """
        每次状态切换都实时从磁盘读取对应 PNG（不缓存到内存全局变量）。
        图片缺失/损坏 → 控制台警告 + 空白占位，程序不崩溃。
        """
        rel = IMAGE_RELS.get(key) or IMAGE_RELS["nothing"]
        path = os.path.join(ASSET_ROOT, rel)
        pm = QPixmap(path)          # 原生尺寸解码，不做任何强制缩放
        if pm.isNull():
            print(f"[鲸鱼娘] 【警告】图片加载失败，使用空白占位继续运行：{path}")
            pm = self._make_blank_placeholder(key)
        return pm

    def _set_image(self, key: str) -> None:
        """状态切换：实时读盘换图；窗口跟随图片原生尺寸，气泡自动重新贴靠。"""
        pm = self._load_state_pixmap(key)
        self._cur_key = key
        self._pixmap = pm
        # 窗口跟随图片原生尺寸自动变化（图片宽高不一致时也会自动适配）
        if self.width() != pm.width() or self.height() != pm.height():
            self.resize(pm.width(), pm.height())
        if self._bubble is not None:
            # 气泡以窗口（左上角+尺寸）为基准自动适配偏移
            self._bubble.place_above(self)
        self.update()

    # ================= 气泡控制（单例 / 3 秒 / 跟随） =================

    def _show_speech(self, text: str) -> None:
        """
        弹出台词：立刻销毁上一个气泡 → 新建气泡显示 3 秒（全局唯一气泡）。
        窗口隐藏期间不弹任何气泡（后台定时器/RAG/API 照常运行，画面静默）。
        """
        if self._hidden:
            return
        self._kill_bubble()
        bubble = SpeechBubble(text)
        bubble.place_above(self)
        self._bubble = bubble
        bubble.show()
        self._bubble_timer.start()

    def _kill_bubble(self) -> None:
        """销毁当前气泡（若有）。"""
        self._bubble_timer.stop()
        if self._bubble is not None:
            b, self._bubble = self._bubble, None
            b.close()          # WA_DeleteOnClose 自动回收

    def moveEvent(self, event) -> None:  # noqa: N802 —— 气泡跟随桌宠移动
        super().moveEvent(event)
        if self._bubble is not None and self.isVisible():
            self._bubble.place_above(self)

    # ================= idle 待机状态机 =================

    def _apply_idle_stage(self) -> None:
        self._set_image(IDLE_ORDER[self._stage_idx])

    def _start_stage_timer(self, ms: int) -> None:
        self._stage_remaining = ms
        self._stage_timer.setInterval(ms)
        self._stage_timer.start()

    def _start_nothing_timer(self) -> None:
        self._nothing_timer.start()

    def _stop_nothing_timer(self) -> None:
        self._nothing_timer.stop()

    def _idle_start(self) -> None:
        """启动 idle 待机：周期重置从 nothing 开始（240s），开启 30s 待机台词计时。
        幂等：仅允许从“尚未启动”状态启动一次（cheerup 3 秒结束/素材缺失后调用）。"""
        if self._idle_started:
            return
        self._idle_started = True
        self._state = "idle"
        self._stage_idx = 0
        self._idle_paused = False
        self._apply_idle_stage()             # 切回 idle nothing.png
        self._start_stage_timer(IDLE_MS["nothing"])
        self._start_nothing_timer()
        print("[鲸鱼娘] 【待机开始】周期已重置：nothing(240s) → eat(30s) → think(30s)")

    def _pause_idle(self) -> None:
        """离开 idle 进入高优先级状态时：暂停 idle 阶段计时与 30s 待机台词计时。"""
        if self._state != "idle":
            return
        r = self._stage_timer.remainingTime()
        if r is not None and r >= 0:
            self._stage_remaining = r
        self._stage_timer.stop()
        self._stop_nothing_timer()
        self._idle_paused = True

    def _back_to_idle(self) -> None:
        """
        回到 idle：接续之前计时进度（不重置 5 分钟周期）。
        若 idle 待机尚未启动（cheerup_show 未播完即被打断等），则此刻全新启动待机循环。
        """
        self._state = "idle"
        if not self._idle_started:
            self._idle_start()               # 待机计时此刻才允许启动
            return
        if self._idle_paused:
            self._idle_paused = False
            self._start_stage_timer(self._stage_remaining)
            if self._stage_idx == 0:
                self._start_nothing_timer()
        self._apply_idle_stage()

    # ================= 登场动画 cheerup_show =================

    def _cheerup_asset_available(self) -> bool:
        """登场素材是否存在且可解码（缺失/损坏 → 警告并跳过登场效果）。"""
        path = os.path.join(ASSET_ROOT, IMAGE_RELS.get("cheerup") or "")
        if not os.path.exists(path):
            print(f"[鲸鱼娘] 【警告】登场素材缺失，跳过登场效果：{path}")
            return False
        try:
            pm = QPixmap(path)
        except Exception as exc:  # noqa: BLE001 —— 解码异常视为损坏
            print(f"[鲸鱼娘] 【警告】登场素材损坏，跳过登场效果：{path}（{exc}）")
            return False
        if pm.isNull():
            print(f"[鲸鱼娘] 【警告】登场素材损坏，跳过登场效果：{path}")
            return False
        return True

    def play_entrance(self) -> bool:
        """
        登场动画（启动 / 隐藏恢复）：
          1) 素材可用：切 cheerup.png + 弹固定气泡「DeepSeek鲸鱼娘登场！」；
             进入 cheerup_show 状态 3 秒；3 秒后才切回 idle nothing 并启动/恢复待机计时。
          2) 素材缺失/损坏 → 警告并直接跳过，立刻进入待机（绝不卡死）。
          3) 已处于 cheerup_show → 幂等返回。
        """
        if self._state == "cheerup_show":
            return True
        if not self._cheerup_asset_available():
            # 容错：跳过登场图片与气泡，立刻启动待机（不阻塞流程、不崩溃）
            print("[鲸鱼娘] 【登场】素材缺失，跳过登场效果，直接进入待机。")
            if not self._idle_started:
                self._idle_start()
            return False
        if self._click_timer.isActive():
            self._click_timer.stop()
        # 若待机已在运行（隐藏恢复场景）→ 先暂停保存进度
        if self._idle_started and self._state == "idle":
            self._pause_idle()
        self._state = "cheerup_show"
        self._set_image("cheerup")
        self._show_speech(ENTRANCE_SPEECH)     # 气泡 3 秒（全局规则）
        self._cheerup_timer.start()
        print("[鲸鱼娘] 【登场】cheerup_show（3 秒后进入待机）…")
        return True

    def _cancel_cheerup(self) -> None:
        """打断 cheerup_show（更高优先级状态切入时调用）。"""
        self._cheerup_timer.stop()

    def _on_cheerup_timeout(self) -> None:
        """cheerup_show 3 秒结束：切回 idle nothing，此刻才启动/恢复待机计时。"""
        if self._state != "cheerup_show":
            return
        print("[鲸鱼娘] 【登场结束】3 秒到 → 切回 idle nothing，开始待机循环。")
        self._back_to_idle()

    def _on_stage_timeout(self) -> None:
        """idle 当前阶段耗尽 → 按固定顺序切下一阶段；eat/think 入场弹固定台词。"""
        self._stage_idx = (self._stage_idx + 1) % len(IDLE_ORDER)
        stage = IDLE_ORDER[self._stage_idx]
        if stage == "eat":
            self._stop_nothing_timer()          # eat/think 阶段关闭 30s 待机台词
            self._apply_idle_stage()
            self._show_speech(EAT_SPEECH)       # 切至 eat.png 瞬间
        elif stage == "think":
            self._apply_idle_stage()
            self._show_speech(THINK_SPEECH)     # 切至 think.png 瞬间
        else:                                   # nothing
            self._apply_idle_stage()
            self._start_nothing_timer()         # 回 nothing 阶段重开 30s 待机台词
        print(f"[鲸鱼娘] 【待机轮转】→ {stage}")
        self._start_stage_timer(IDLE_MS[stage])

    def _pop_nothing_line(self) -> None:
        """仅 nothing 待机阶段且未被暂停时：每 30s 随机弹一句 nothing.txt 台词。"""
        if self._state != "idle" or self._idle_paused:
            return
        if IDLE_ORDER[self._stage_idx] != "nothing":
            return
        pool = load_talk_pool(TALK_NOTHING_REL, NOTHING_FALLBACK)
        line = random.choice(pool)
        print(f"[鲸鱼娘] 【待机台词】{line}")
        self._show_speech(line)

    # ================= touch（左键单击交互） =================

    def _do_touch(self) -> None:
        """单击判定成立：切 touch.png + 随机 touch.txt 台词 + 3 秒倒计时。"""
        if self._state in ("query", "pickup", "cheerup_show"):
            return      # cheerup_show 3 秒内屏蔽 touch（与 query/pickup 一致）
        # 高优先级 touch 打断低优先级 file_import / view_files
        if self._state == "file_import":
            self._file_import_timer.stop()
        elif self._state == "view_files":
            self._stop_view_watch()          # 交互即结束查看状态（降级方案）
        if self._state == "idle":
            self._pause_idle()
        # 若上次 touch 的 3 秒倒计时未结束 → 清除旧计时，重新开始 3 秒
        if self._touch_timer.isActive():
            self._touch_timer.stop()
        self._state = "touch"
        self._set_image("touch")
        pool = load_talk_pool(TALK_TOUCH_REL, TOUCH_FALLBACK)
        line = random.choice(pool)
        print(f"[鲸鱼娘] 【点击交互】{line}")
        self._show_speech(line)
        self._touch_timer.start()

    def _on_touch_timeout(self) -> None:
        """touch 3 秒结束：回 nothing，恢复 idle 待机计时。"""
        if self._state != "touch":
            return
        print("[鲸鱼娘] 【点击结束】3 秒倒计时结束，恢复待机。")
        self._back_to_idle()

    # ================= pickup（拖拽交互） =================

    def _start_pickup(self) -> None:
        """拖拽开始瞬间：切 pickup.png，仅弹一次固定台词；暂停 idle 计时。"""
        if self._state in ("pickup", "query", "cheerup_show"):
            return      # cheerup_show 3 秒内屏蔽 PickUp 拖拽
        if self._click_timer.isActive():
            self._click_timer.stop()
        if self._touch_timer.isActive():
            self._touch_timer.stop()          # 拖拽打断 touch
        if self._state == "file_import":
            self._file_import_timer.stop()    # 拖拽打断 file_import 反馈
        if self._state == "view_files":
            self._stop_view_watch()           # 拖拽即结束查看状态（降级方案）
        if self._state == "idle":
            self._pause_idle()
        self._state = "pickup"
        self._set_image("pickup")
        print(f"[鲸鱼娘] 【拖拽开始】{PICKUP_SPEECH}")
        self._show_speech(PICKUP_SPEECH)

    def _end_pickup(self) -> None:
        """松开结束拖拽：强制回 nothing，恢复 idle 状态机计时（接续进度），并记住新位置。"""
        if self._state != "pickup":
            return
        print("[鲸鱼娘] 【拖拽结束】松开鼠标，恢复待机。")
        self._back_to_idle()
        # 用户手动拖拽后记住窗口位置 → config.json（下次启动恢复）
        save_window_position(self.x(), self.y())

    # ================= query（查询余额，右键菜单触发） =================

    def start_query(self) -> None:
        """进入查询余额状态：切 nomoney.png、暂停 idle、屏蔽 touch/拖拽。"""
        self._ensure_visible_for_action()        # 隐藏状态下先恢复显示
        if self._state == "query":
            return
        if self._click_timer.isActive():
            self._click_timer.stop()
        if self._state == "touch":
            self._touch_timer.stop()
        if self._state == "file_import":
            self._file_import_timer.stop()    # query 打断 file_import 反馈
        if self._state == "view_files":
            self._stop_view_watch()
        if self._state == "cheerup_show":
            self._cancel_cheerup()          # query（更高优先级）打断 cheerup_show
        if self._state == "idle":
            self._pause_idle()
        self._state = "query"
        self._set_image("nomoney")
        print("[鲸鱼娘] 【查询余额】进入查询状态（nomoney.png，等待接口返回…）")

        self._query_seq += 1
        seq = self._query_seq
        api_key = read_api_key()
        if not api_key:
            # 密钥缺失/为空：直接提示获取失败，不发起网络请求，程序不崩溃
            print("[鲸鱼娘] 【查询余额】未读取到有效 APIKEY，直接提示获取失败。")
            self._on_balance_result(seq, BALANCE_FAIL_TEXT)
            return
        # 本地 requests 在主程序内部完成（独立线程，10 秒超时）
        threading.Thread(target=self._balance_job,
                         args=(api_key, self._balance_bridge, seq),
                         daemon=True).start()

    @staticmethod
    def _balance_job(api_key: str, bridge: BalanceBridge, seq: int) -> None:
        """工作线程：请求 /user/balance 并把展示文案发回主线程。"""
        bridge.result.emit(seq, request_balance_text(api_key))

    def _on_balance_result(self, seq: int, text: str) -> None:
        """余额结果回到主线程：序号过期或已退出查询则丢弃，避免旧结果串台。"""
        if seq != self._query_seq or self._state != "query":
            return
        print(f"[鲸鱼娘] 【余额结果】{text}")
        self._show_speech(text)

    def exit_query(self) -> None:
        """点击桌宠任意位置退出查询：销毁余额气泡，回 nothing，恢复 idle 计时。"""
        if self._state != "query":
            return
        print("[鲸鱼娘] 【退出查询】点击退出查询状态，恢复待机。")
        self._kill_bubble()
        self._back_to_idle()

    # ================= RAG：知识库刷新 / 文件导入 =================

    def refresh_rag(self) -> None:
        """刷新 RAG 知识库文本（打开聊天窗口时、文件导入成功后调用）。"""
        info = load_rag_text()
        self.rag_text = info["text"]
        self.rag_loaded = info["loaded"]
        self.rag_combined_truncated = info["combined_truncated"]
        self.rag_doc_truncated = info["doc_truncated"]
        if self._chat_window is not None:
            self._chat_window.update_rag_label()
        print(f"[鲸鱼娘] 【知识库刷新】已加载 {self.rag_loaded}/{RAG_MAX_TOTAL} 字，"
              f"跳过损坏文档 {info['skipped']} 个。")

    def _ensure_visible_for_action(self) -> None:
        """托盘触发文件/查看动作时，若主窗口被隐藏则先还原（便于看到反馈）。"""
        if self.isHidden():
            self.show()
            self.raise_()
            self.activateWindow()

    def start_add_documents(self) -> None:
        """右键菜单【添加资料文件】：弹出系统文件对话框，多选 .txt/.docx 导入。"""
        if self._state in ("pickup", "touch", "query"):
            print("[鲸鱼娘] 【添加资料】处于高优先级状态，本次命令已忽略。")
            return
        self._ensure_visible_for_action()
        ensure_rag_dir()
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择要添加的资料文件（支持 .txt / .docx）", "",
            "资料文件 (*.txt *.docx);;所有文件 (*.*)")
        if paths:
            self._handle_import_paths(paths)

    def _handle_import_paths(self, paths: list) -> None:
        """
        统一导入入口（菜单多选 / 外部文件拖拽共用）：
          - 高优先级状态（pickup/touch/query）下直接忽略，不触发任何反馈；
          - 全部成功 → 成功反馈；存在失败 → 失败反馈（抖动 + 错误气泡）。
        """
        if self._state in ("pickup", "touch", "query"):
            print("[鲸鱼娘] 【添加资料】高优先级状态中，文件拖拽导入不触发反馈。")
            return
        ok_all = True
        any_ok = False
        for path in paths:
            moved = self._import_document(path)
            ok_all = ok_all and moved
            any_ok = any_ok or moved
        if any_ok:
            self.refresh_rag()      # 文件导入成功后自动刷新知识库（无需重启）
        self._enter_file_import(ok_all)

    def _import_document(self, path: str) -> bool:
        """把单个文档移入 RAG：仅 .txt/.docx；重名自动追加序号不覆盖；异常 → False。"""
        try:
            if not os.path.isfile(path):
                print(f"[鲸鱼娘] 【导入失败】文件不存在：{path}")
                return False
            if not is_supported_document(path):
                print(f"[鲸鱼娘] 【导入失败】不支持的格式（仅 .txt/.docx）：{path}")
                return False
            ensure_rag_dir()
            stem, ext = os.path.splitext(os.path.basename(path))
            target = os.path.join(RAG_DIR, stem + ext)
            counter = 1
            while os.path.exists(target):        # 重名自动加序号，绝不覆盖
                target = os.path.join(RAG_DIR, f"{stem}({counter}){ext}")
                counter += 1
            shutil.move(path, target)            # 移动（非复制）到 RAG
            print(f"[鲸鱼娘] 【导入成功】{os.path.basename(path)} → {target}")
            return True
        except Exception as exc:  # noqa: BLE001 —— 权限不足/被占用/其他异常
            print(f"[鲸鱼娘] 【导入失败】移动文件异常（{type(exc).__name__}）：{exc}")
            return False

    # ================= file_import（导入反馈状态，持续 3 秒） =================

    def _enter_file_import(self, ok: bool) -> None:
        """进入 file_import：成功 true.png+“吃饱了...嗝...”；失败 wrong.png+抖动+气泡。"""
        if self._state in ("pickup", "touch", "query"):
            return
        if self._click_timer.isActive():
            self._click_timer.stop()
        if self._state == "file_import":
            self._file_import_timer.stop()     # 重新开始 3 秒倒计时
        if self._state == "view_files":
            self._stop_view_watch()
        if self._state == "cheerup_show":
            self._cancel_cheerup()          # file_import（更高优先级）打断 cheerup_show
        if self._state == "idle":
            self._pause_idle()
        self._state = "file_import"
        if ok:
            self._set_image("true")
            self._show_speech(FILE_OK_SPEECH)          # 吃饱了...嗝...
        else:
            self._set_image("wrong")
            self._show_speech(FILE_FAIL_SPEECH)        # 呕...你给我喂的啥？
            self._start_shake()                        # 窗口抖动 0.3 秒
        print(f"[鲸鱼娘] 【导入反馈】file_import：{'成功' if ok else '失败'}（3 秒后恢复待机）")
        self._file_import_timer.start()

    def _on_file_import_timeout(self) -> None:
        """file_import 3 秒结束：切回 idle nothing，恢复待机计时（接续原进度）。"""
        if self._state != "file_import":
            return
        print("[鲸鱼娘] 【导入反馈结束】3 秒到，恢复待机。")
        self._back_to_idle()

    def _start_shake(self) -> None:
        """窗口抖动 0.3 秒：左右小幅晃动后回到原位（导入失败反馈）。"""
        self._shake_base = self.pos()
        self._shake_tick = 0
        self._shake_active = True
        self._shake_timer.start()

    def _stop_shake(self) -> None:
        if not self._shake_active:
            return
        self._shake_active = False
        self._shake_timer.stop()
        if self.pos() != self._shake_base:
            self.move(self._shake_base)

    def _on_shake_tick(self) -> None:
        self._shake_tick += 1
        total = max(1, int(SHAKE_MS / SHAKE_STEP_MS))
        if self._shake_tick > total:
            self._stop_shake()
            return
        dx = 10 if (self._shake_tick % 2 == 1) else -10
        base = self._shake_base
        if base:
            self.move(QPoint(base.x() + dx, base.y()))

    # ================= view_files（查看资料状态） =================

    def start_view_files(self) -> None:
        """右键菜单【查看已有资料】：打开 RAG 文件夹，进入 view_files 状态。"""
        if self._state in ("pickup", "touch", "query", "file_import",
                           "cheerup_show"):
            print("[鲸鱼娘] 【查看资料】处于更高优先级状态，命令已忽略（不切换图片）。")
            return
        if self._state == "view_files":
            print("[鲸鱼娘] 【查看资料】已在查看状态中。")
            return
        self._ensure_visible_for_action()
        if self._click_timer.isActive():
            self._click_timer.stop()
        if self._state == "idle":
            self._pause_idle()
        self._state = "view_files"
        self._set_image("think")                       # 复用 think.png
        count = count_rag_documents()                  # 实时统计 .txt+.docx
        self._show_speech(VIEW_COUNT_SPEECH.format(count=count))
        print(f"[鲸鱼娘] 【查看资料】view_files 状态，当前已收纳 {count} 个资料。")

        self._view_open = False
        self._view_poll_count = 0
        self._view_timer.start()                       # 轮询监听文件夹窗口关闭

        # RAG 文件夹不存在则先创建再打开；打开失败给气泡提示，不崩溃
        ensure_rag_dir()
        if not open_folder_in_explorer(RAG_DIR):
            print(f"[鲸鱼娘] 【警告】打开 RAG 文件夹失败：{RAG_DIR}")
            self._show_speech(VIEW_OPEN_FAIL_SPEECH)   # 覆盖计数气泡（全局唯一气泡）
            self._view_poll_count = VIEW_OPEN_TRIES + 1  # 不再空等窗口，靠交互降级退出

    def _on_view_poll(self) -> None:
        """
        轮询监听资源管理器窗口：
         - 窗口尚未出现 → 持续等待（超过尝试次数即停表，靠用户交互降级退出）；
         - 窗口曾出现 → 一旦消失立即自动结束 view_files 并恢复待机。
        """
        if self._state != "view_files":
            self._view_timer.stop()
            return
        if not self._view_open:
            self._view_poll_count += 1
            if find_folder_window(RAG_DIR):
                self._view_open = True
                print("[鲸鱼娘] 【查看资料】已检测到 RAG 文件夹窗口，开始监听关闭。")
            elif self._view_poll_count > VIEW_OPEN_TRIES:
                # 无法精准监听（explorer 复用/标题不同等）→ 停表，改由交互降级
                print("[鲸鱼娘] 【查看资料】未检测到独立窗口，改用“任意交互退出”降级方案。")
                self._view_timer.stop()
            return
        if not find_folder_window(RAG_DIR):
            print("[鲸鱼娘] 【查看资料】RAG 文件夹窗口已关闭，自动恢复待机。")
            self._stop_view_watch()
            self._back_to_idle()

    def _stop_view_watch(self) -> None:
        """停止文件夹窗口监听（交互结束 / 窗口关闭 / 被更高优先级状态打断时）。"""
        self._view_timer.stop()

    # ================= 外部文件拖拽导入（与 PickUp 严格区分） =================

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        """外部文件拖入桌宠窗口：接受文件拖拽（拖拽移动桌宠走 mouse 事件，互不干扰）。"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        """外部文件松开：收集本地文件路径并走统一导入流程（自动校验后缀）。"""
        event.acceptProposedAction()
        paths = [u.toLocalFile() for u in event.mimeData().urls()
                 if u.isLocalFile()]
        if not paths:
            return
        print(f"[鲸鱼娘] 【文件拖入】收到 {len(paths)} 个文件，开始导入校验…")
        self._handle_import_paths(paths)

    # ================= 鼠标事件 =================

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            # 新一次按下即新手势：清除可能残留的“双击第二下释放”标记
            self._suppress_next_release = False
            if self._state in ("query", "cheerup_show"):
                # query：屏蔽 touch/拖拽（释放退出查询）；cheerup_show：3 秒内屏蔽触摸/拖拽
                return
            self._pressing = True
            self._drag_active = False
            self._press_global = event.globalPosition().toPoint()
            self._drag_offset = self._press_global - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._state in ("query", "cheerup_show"):
            return                              # query/cheerup_show 屏蔽 PickUp 拖拽
        if (event.buttons() & Qt.LeftButton) and self._pressing:
            gpos = event.globalPosition().toPoint()
            if not self._drag_active:
                # 按下且移动达到阈值才算拖拽；单纯按下不动只算点击
                if (gpos - self._press_global).manhattanLength() >= DRAG_THRESHOLD_PX:
                    self._drag_active = True
                    self._start_pickup()
            if self._drag_active and self._state == "pickup":
                self.move(self._clamp_pos(gpos - self._drag_offset))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            if self._state == "query":
                self._pressing = False
                self._drag_offset = None
                self.exit_query()               # 点击任意处退出查询
                return
            if self._suppress_next_release:     # 双击第二下的释放 → 无动作
                self._suppress_next_release = False
                self._pressing = False
                self._drag_offset = None
                return
            if self._pressing:
                was_drag = self._drag_active
                self._pressing = False
                self._drag_active = False
                self._drag_offset = None
                if was_drag:
                    self._end_pickup()          # 拖拽结束
                else:
                    # 单击延迟到双击判定窗口之后，确保“双击无动作”
                    self._click_timer.start()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        """左键双击：无任何动作（不再弹聊天框）；消费掉双击相关的单击/释放。"""
        if self._click_timer.isActive():
            self._click_timer.stop()
        self._suppress_next_release = True   # 双击第二下的释放不触发任何动作
        self._pressing = False
        self._drag_offset = None
        super().mouseDoubleClickEvent(event)

    def _build_context_menu(self) -> QMenu:
        """
        右键菜单（顺序严格 + UI 样式）：
        聊聊天 / 查询余额 / 添加资料文件 / 查看已有资料 / 更改API-KEY / 重置位置
        —— 分隔线 ——  隐藏鲸鱼娘（隐藏时显示为“显示鲸鱼娘”） / 退出（红色字体）
        """
        menu = QMenu(self)
        act_chat = QAction("聊聊天", menu)
        act_balance = QAction("查询余额", menu)
        act_add = QAction("添加资料文件", menu)
        act_view = QAction("查看已有资料", menu)
        act_key = QAction("更改API-KEY", menu)
        act_reset = QAction("重置位置", menu)
        hide_text = "显示鲸鱼娘" if self.isHidden() else "隐藏鲸鱼娘"
        act_hide = QAction(hide_text, menu)
        act_chat.triggered.connect(self.open_chat_window)
        act_balance.triggered.connect(self.start_query)
        act_add.triggered.connect(self.start_add_documents)
        act_view.triggered.connect(self.start_view_files)
        act_key.triggered.connect(self.change_api_key)
        act_reset.triggered.connect(self.reset_position)
        act_hide.triggered.connect(self.toggle_hide_whale)
        for act in (act_chat, act_balance, act_add, act_view, act_key, act_reset):
            menu.addAction(act)
        menu.addSeparator()                       # 「重置位置」与「隐藏鲸鱼娘」之间
        menu.addAction(act_hide)
        menu.addAction(make_red_quit_action(menu, self.quit_app))   # 红色【退出】
        return menu

    def contextMenuEvent(self, event) -> None:  # noqa: N802 —— 右键：光标处弹菜单
        menu = self._build_context_menu()
        menu.exec(event.globalPos())
        event.accept()

    def _clamp_pos(self, pos: QPoint) -> QPoint:
        """屏幕边界钳制：宠物至少留一部分在屏幕内（防拖丢）。"""
        screen = self.screen() if self.screen() else QApplication.primaryScreen()
        if screen is None:
            return pos
        geo = screen.availableGeometry()
        x = max(geo.left() - self.width() + 60,
                min(pos.x(), geo.right() - 60))
        y = max(geo.top(), min(pos.y(), geo.bottom() - 60))
        return QPoint(int(x), int(y))

    # ================= 聊聊天（右键菜单） =================

    def open_chat_window(self) -> None:
        """弹出聊天子窗口（就近放在宠物右侧）；打开聊天窗口即刷新 RAG 知识库。
        边界规则：窗口隐藏时先自动恢复显示再执行。"""
        self._ensure_visible_for_action()
        if self._chat_window is None:
            self._chat_window = ChatWindow(pet=self)
            app = QApplication.instance()
            if app is not None:
                app._chat_window = self._chat_window
        else:
            self.refresh_rag()          # 每次打开都刷新（含再次打开）
            self._chat_window.update_rag_label()
        self._chat_window.show_and_activate(self.frameGeometry())
        print("[鲸鱼娘] 【聊聊天】已弹出聊天窗口。")

    # ================= 更改 API-KEY（右键菜单） =================

    def change_api_key(self) -> None:
        """
        右键菜单【更改API-KEY】：弹出模态输入对话框；【先连通测试，通过后才覆盖
        写入 API-KEY.txt】：
          - 成功 → 覆盖写入新密钥、更新内存密钥、弹“注册成功！”3 秒自动关闭；
          - 失败 → 【不覆盖原密钥文件】、聊天框红字“API_KEY有误，请重新输入。”，
            弹窗保留继续修改（旧密钥保持有效）；
          - 取消 → 关闭弹窗，未发生任何写入，原密钥保持不变；
          - 测试通过但写盘失败 → 弹窗提示后退出程序。
        （弹窗为模态，期间桌宠点击/拖拽等交互一律被忽略。）
        """
        if self.isHidden():
            self.show()          # 从托盘触发时先还原主窗口，便于看到结果
            self.raise_()
        dlg = ChangeApiKeyDialog(owner_pet=self, parent=None)
        if dlg.exec() == QDialog.Accepted:
            # 内存密钥已在对话框内更新（测试通过并成功写入后才 accept）
            print("[鲸鱼娘] 【更改API-KEY】新密钥已启用（内容保密）。")
            show_auto_close_message("DeepSeek API", KEY_REGISTERED_TEXT)
            return
        # 取消 / 关闭：旧密钥文件未被覆盖（只有新密钥测试通过后才落盘），无需还原
        print("[鲸鱼娘] 【更改API-KEY】已取消，密钥未修改（原密钥保持有效）。")

    # ================= 退出 / 清理 / 托盘 =================

    def attach_tray(self, tray) -> None:
        """由 main() 注册系统托盘（不支持托盘时为 None，走关窗即退出回退逻辑）。"""
        self._tray = tray

    def quit_app(self) -> None:
        """【退出】：先保存当前窗口位置到 config.json，再完全结束进程。
        aboutToQuit → _cleanup 统一停止定时器/销毁气泡/销毁托盘对象。"""
        print("[鲸鱼娘] 【退出】正在清理并完全退出程序…")
        save_window_position(self.x(), self.y())   # 退出前保存当前位置（五.6）
        self._quitting = True       # 允许桌宠/聊天窗口真正关闭（不阻断退出）
        if self._chat_window is not None and self._chat_window.isVisible():
            self._chat_window.close()
        app = QApplication.instance()
        if app is not None:
            app.quit()          # aboutToQuit → _cleanup 统一清理

    def _cleanup(self) -> None:
        """停止全部定时器、销毁气泡组件、销毁托盘对象，杜绝资源残留。"""
        for timer in (self._stage_timer, self._nothing_timer, self._touch_timer,
                      self._bubble_timer, self._click_timer,
                      self._file_import_timer, self._shake_timer,
                      self._view_timer, self._cheerup_timer):
            try:
                timer.stop()
            except RuntimeError:
                pass
        self._stop_shake()
        self._kill_bubble()
        if self._tray is not None:
            tray, self._tray = self._tray, None
            try:
                tray.hide()
                tray.deleteLater()
            except RuntimeError:
                pass
            print("[鲸鱼娘] 【退出】已销毁系统托盘图标。")
        print("[鲸鱼娘] 【退出完成】已停止全部定时器并销毁气泡组件。")

    # ================= 隐藏鲸鱼娘 / 显示还原（隐藏期间后台继续运行） =================

    def hide_whale(self) -> None:
        """【隐藏鲸鱼娘】：主窗口隐藏，托盘图标常驻；定时器 / RAG / API 后台继续运行。"""
        if not self.isHidden():
            print("[鲸鱼娘] 【隐藏】鲸鱼娘暂时藏起来了（双击托盘图标可唤出）。")
            self.hide()

    def show_whale(self, greet: bool = True) -> None:
        """恢复显示主窗口；greet=True 时执行登场动画（cheerup.png + 登场气泡 3 秒）。"""
        if self.isHidden():
            self.show()
        self.raise_()
        self.activateWindow()
        if greet:
            print("[鲸鱼娘] 【显示】鲸鱼娘回来了，播放登场动画。")
            self.play_entrance()

    def toggle_hide_whale(self) -> None:
        """右键菜单【隐藏鲸鱼娘】/【显示鲸鱼娘】切换。"""
        if self.isHidden():
            self.show_whale(greet=True)
        else:
            self.hide_whale()

    def closeEvent(self, event) -> None:  # noqa: N802
        """
        窗口关闭按钮/Alt+F4：
          - 完整退出中(_quitting) → 直接接受，配合 app.quit 正常结束；
          - 有托盘 → 只隐藏主窗口，驻留后台托盘运行；
          - 无托盘（系统不支持等）→ 回退为关窗即完全退出。
        """
        if self._quitting:
            event.accept()
            return
        if self._tray is not None:
            print("[鲸鱼娘] 【窗口关闭】隐藏到系统托盘继续运行（托盘右键【退出】可结束）。")
            self.hide()
            event.ignore()
        else:
            self.quit_app()
            event.accept()

    # ================= 初始定位（默认右下角；config.json 有效时启动/退出恢复该位置） =================

    def _compute_center_geometry(self) -> QRect:
        """
        计算“默认位置”：桌面右下角、任务栏上方。
        使用桌面可用区域（已排除任务栏），让窗口右下角与可用区域右下角对齐。
        当 config.json 缺失/无效时用作启动位置；【重置位置】也会重新计算此坐标。
        """
        screen = QApplication.primaryScreen()
        if screen is None:
            return QRect(0, 0, self.width(), self.height())
        geo = screen.availableGeometry()          # 可用区域：排除任务栏/停靠栏
        x = geo.left() + geo.width() - self.width()
        y = geo.top() + geo.height() - self.height()
        print(f"[鲸鱼娘] 【启动定位】可用区域 {geo.width()}x{geo.height()}，"
              f"窗口 {self.width()}x{self.height()} → 右下角 ({x}, {y})")
        return QRect(int(x), int(y), self.width(), self.height())

    def home_geometry(self) -> QRect:
        """默认（右下角）启动几何；config.json 优先逻辑在 main() 中处理。"""
        return self._home_rect

    def reset_position(self) -> None:
        """右键【重置位置】：立刻回到桌面右下角（任务栏上方），并同步 config.json。"""
        self._ensure_visible_for_action()        # 隐藏状态下先恢复显示
        rect = self._compute_center_geometry()   # 按当前分辨率实时重算右下角
        self._home_rect = rect
        self.setGeometry(rect)
        self.raise_()
        save_window_position(self.x(), self.y())
        print(f"[鲸鱼娘] 【重置位置】已移动到右下角 ({self.x()}, {self.y()})。")

    # ================= 绘制 =================

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pm = getattr(self, "_pixmap", None)
        if pm is not None and not pm.isNull():
            painter.drawPixmap(0, 0, pm)
        else:
            painter.fillRect(self.rect(), QColor(255, 255, 255, 200))
        painter.end()

    def showEvent(self, event) -> None:  # noqa: N802 —— 显示时清除隐藏标记
        super().showEvent(event)
        self._hidden = False

    def hideEvent(self, event) -> None:  # noqa: N802 —— 隐藏时标记，隐藏期间不弹气泡、后台继续
        self._hidden = True
        self._kill_bubble()
        self._click_timer.stop()
        self._shake_timer.stop()
        super().hideEvent(event)


# ================================================================================
# 六、程序入口
# ================================================================================

def main() -> None:
    print("[鲸鱼娘] 【程序已启动】鲸鱼娘桌宠（asset_library 素材 · 状态机模式）")

    app = QApplication(sys.argv)
    app.setApplicationName("WhaleGirlPet")
    app.setQuitOnLastWindowClosed(False)

    # ---- 程序启动第一件事：API 密钥检测 / 初始化 ----
    # 存在有效 API-KEY.txt → 直接继续（不测试不弹窗）；不存在/为空 → 模态输入对话框，
    # 写入后自动连通性测试；未完成配置（退出程序/空输入）→ 直接结束进程。
    if not ensure_api_key_at_startup():
        print("[鲸鱼娘] 【程序退出】API 密钥未配置完成，桌宠未启动。")
        return

    pet = DesktopPet()
    app._pet = pet
    app.aboutToQuit.connect(pet._cleanup)

    # ---- 初始位置：config.json 有有效坐标 → 恢复上次位置；否则默认右下角 ----
    home = pet.home_geometry()
    saved = load_window_position()
    if saved is not None:
        x, y = clamp_position_to_screen(saved[0], saved[1],
                                        pet.width(), pet.height())
        home.moveTopLeft(QPoint(int(x), int(y)))
        print(f"[鲸鱼娘] 【位置恢复】使用 config.json 坐标 ({x}, {y})。")
    else:
        print("[鲸鱼娘] 【位置恢复】无有效 config.json，使用默认右下角位置。")
    pet.setGeometry(home)
    pet.show()
    pet.raise_()
    pet.activateWindow()
    print(f"[鲸鱼娘] 宠物已显示 ({pet.x()}, {pet.y()})。")

    # ---- 登场动画：正式显示后切换 cheerup.png + 登场气泡，3 秒后进入待机 ----
    pet.play_entrance()

    # ---- 系统托盘：程序启动即注册，常驻右下角（含隐藏图标列表）----
    # 系统不支持托盘 → 回退：关闭窗口直接完全退出（pet._tray 保持 None）。
    tray = None
    if QSystemTrayIcon.isSystemTrayAvailable():
        try:
            tray = PetTrayIcon(pet)
            pet.attach_tray(tray)
            app._tray = tray     # 强引用，防垃圾回收
            print("[鲸鱼娘] 系统托盘注册成功（右键托盘：聊聊天/查询余额/添加资料文件/"
                  "查看已有资料/更改API-KEY/重置位置/隐藏鲸鱼娘/退出；"
                  "双击还原窗口；仅【退出】结束进程）。")
        except Exception as exc:  # noqa: BLE001 —— 托盘失败不影响桌宠本体运行
            tray = None
            pet.attach_tray(None)
            print("[鲸鱼娘] 【托盘初始化失败】程序继续运行（关窗将直接退出）：", exc)
    else:
        print("[鲸鱼娘] 【托盘不可用】当前系统不支持系统托盘："
              "关闭窗口将直接完全退出（回退兼容逻辑）。")

    sys.exit(app.exec())


if __name__ == "__main__":
    # 打包说明：
    #   pip install pyinstaller
    #   pyinstaller -F -w -n WhaleGirlPet --add-data "asset_library;asset_library" main.py
    #   （PySide6、requests 会被 PyInstaller 自动收集进 exe；
    #     分发时 exe 与 asset_library 文件夹必须同级，
    #     用户直接替换 exe 同级 asset_library/move/** 里的 png 即可换图，
    #     无需修改代码、无需重新打包。）
    main()
