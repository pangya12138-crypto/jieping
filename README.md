# 无需本地安装 Python 的构建方式

这个压缩包不能在当前聊天环境里直接生成 Windows EXE，但可以让 GitHub 的 Windows 服务器代为构建。

## 操作

1. 登录 GitHub，新建一个空仓库。
2. 上传本压缩包内的全部文件，注意 `.github` 文件夹也要上传。
3. 打开仓库的 `Actions` 页面。
4. 选择 `Build Portable ComicPDF EXE`。
5. 点击 `Run workflow`。
6. 等待构建完成。
7. 在构建页面底部下载 `ComicPDF-portable`。

下载并解压后可直接运行 `ComicPDF.exe`，本机不需要安装 Python。

## 说明

最终文件会比较大，因为它包含运行环境和 Chromium 浏览器。
GitHub Actions 构建产物默认保留 7 天。
