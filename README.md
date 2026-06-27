# 操作系统教材

这是《操作系统》教材的在线阅读版本。Windows 用户可以用 Git 获取教材，并在后续更新时一键同步最新内容。

## 第一次获取

先安装 Git for Windows：

https://git-scm.com/download/win

然后在想保存教材的目录打开 PowerShell、命令提示符或 Git Bash，运行：

```powershell
git clone https://github.com/OutsiderK/OS_Textbook.git
```

克隆完成后进入目录：

```powershell
cd OS_Textbook
```

## 以后更新

Windows 用户可以直接双击：

```text
windows-pull-latest.cmd
```

脚本会自动拉取最新内容。你也可以在仓库目录手动运行：

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
```

## 如果本地改动导致更新失败

先查看哪些文件被改过：

```powershell
git status
```

如果你想保留自己的修改，可以先提交到本地：

```powershell
git add 文件名
git commit -m "docs: 保存本地修改"
```

然后重新运行 `windows-pull-latest.cmd`。

如果你只是误改了文件，确认不需要保留后，可以放弃对已跟踪文件的修改：

```powershell
git restore 文件名
```

如果失败信息里还有你自己新增但不需要的文件，可以先预览将被删除的文件：

```powershell
git clean -n
```

确认无误后再删除这些未跟踪文件：

```powershell
git clean -f
```

处理完本地改动后，再重新运行 `windows-pull-latest.cmd`。
