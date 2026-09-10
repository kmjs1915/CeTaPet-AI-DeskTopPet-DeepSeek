# CeTaPet-AI-DeskTopPet-DeepSeek
这是一款基于Python开发的桌面AI桌宠，对接DeepSeek模型，支持角色聊天，以及轻量化RAG知识库。
CeTaPet-AI-桌面宠物（鲸鱼娘桌宠）  
<img width="105" height="125" alt="cheerup" src="https://github.com/user-attachments/assets/41965a4a-3c41-4c26-835d-7ff00324da77" />

这是一个使用 Python + PySide6 开发的Windows桌面AI宠物，接入DeepSeek大模型，支持角色对话、本地轻量化RAG文档问答。
本项目是个人学习Demo，由 DeepSeek Harness 和 ChatGPT 辅助生成代码，仅用于编程学习、AI应用实践。  
**⚠️程序需要用户自行准备 DeepSeek API Key，才能启用对话与RAG功能。**


# 请在下载前仔细阅读内容（尤其是最后一条重要提醒！！！）

# ✨ 项目功能

左键点击鲸鱼娘：触发互动动作，弹出对话气泡  
<img width="249" height="249" alt="image" src="https://github.com/user-attachments/assets/c2e519e6-81e2-4bb9-8072-73dd516deedb" />  
右键点击鲸鱼娘呼出菜单  
<img width="166" height="275" alt="image" src="https://github.com/user-attachments/assets/6bdcb40e-58b6-4f74-822e-f25de0642ec1" />
>[!NOTE]
># 那本桌宠亮点在哪？  
>✨**1.文本文件读取：**  
>读取RAG文件夹内 .txt/.docx 文档，支持拖拽文件交给桌宠解析，鲸鱼娘可以阅读文本内容并在对话框进行互动
>你可以将文件拖拽到角色图标，让鲸鱼娘“吃下文件” ,不同的文件鲸鱼娘有不同的反应。  
><img width="110" height="132" alt="true" src="https://github.com/user-attachments/assets/6eaa77cf-34fd-47a8-a3c1-6b0976dd9657" />
><img width="110" height="125" alt="wrong" src="https://github.com/user-attachments/assets/b01be741-eb37-4d3b-8205-5bf6cbde1579" />  
>可以是你的日记，你的期末复习资料，只要你愿意向鲸鱼娘分享！  
>✨**2.素材自定义：**  
>不喜欢deepseek鲸鱼娘的形象？  
>所有角色动作图片、预设对话台词全部放在 asset_library 文件夹，可自行替换asset_library文件夹内图片素材，自定义角色形象

## 🖥️ 运行环境
- 操作系统：Windows 10 / Windows 11
- 运行方式二选一：
  1. 打包成品：直接下载 Release 压缩包解压运行
  2. 源码运行：Python 3.10+，自行安装依赖
 
  
## 📦 使用教程
1. 前往本仓库 Release 页面下载最新版本压缩包
2. 完整解压压缩包（⚠ 必须保证 `鲸鱼娘桌宠.exe` 和 `_internal`文件夹在同一个目录！**不要单独提取exe**）
3. 双击 `鲸鱼娘桌宠.exe` 启动程序
4. 首次运行，输入你自己申请的 DeepSeek API Key
5. 左键点击角色互动；右键打开菜单；将文档拖拽至角色上，自动加入RAG知识库

## 📜 开源协议
本项目使用 MIT License，详见 LICENSE 文件。
> 仅允许个人学习使用；禁止商用。
素材说明：角色图片为ChatGPT AI生成素材。


## 🛠️ 源码运行
```bash
# 安装依赖
pip install pyside6 python-docx
```
```bash
# 启动
python main.py
```
## 🐛 问题反馈
发现Bug或功能建议，可以在 GitHub Issues 提交反馈。

## 🧰 技术栈
- Python + PySide6：桌面GUI、窗口交互、托盘图标
- DeepSeek API：大模型对话
- 简易本地RAG：读取docx/txt文档
- PyInstaller：打包exe，发布Windows桌面程序

> [!CAUTION]
> # ⚠️【重要提醒】API KEY 明文存储！
> 本项目为学习Demo，**未做密钥加密**。请妥善保管你的DeepSeek API密钥，不要分享包含密钥的配置文件。密钥泄露产生的全部费用，由使用者自行承担，开发者不承担任何相关损失。  
> 程序初次启动会要求输入DeepSeek API Key，密钥将明文保存至 asset_library/API-KEY.txt，请务必注意安全！  
> **最后，本项目是我第一个独立开发项目，欢迎各位大佬多多指正，也欢基于本项目迎进行二次开发！！！**


