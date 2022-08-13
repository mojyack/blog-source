## 画面共有がしたい件
この記事では、Gentoo Linux+Swayでスクリーン共有をする、Waylandネイティブな方法を紹介する。

Waylandでスクリーン共有をするためには、アプリケーションが xdg-desktop-portal に対応していればよい。Firefoxなどは対応しているので、ブラウザ上の Discord は xdg-desktop-portal をインストールすればスクリーン共有できるようになる。
問題は対応していないアプリである。例えば Zoom のLinuxクライアント などはこのケースだ。この場合には、OBS Studio でキャプチャした画面を仮想カメラに流して、それを使う戦略を取る。

前提条件として、以下が執筆当時の環境である。  
Linux 5.19.0  
Sway 1.7  
wlroots 0.15.0  
Firefox 103.0.1

また、すでにPipewireを使った音声出力ができていることを想定する。

## xdg-desktop-portal を動かす
これらのパッケージが必要だ。  
```
gui-libs/xdg-desktop-portal-wlr
sys-apps/xdg-desktop-portal
```

特に、これらのUSEフラグを有効にする必要がある。
```
sys-apps/xdg-desktop-portal screencast
```

インストールできたらサービスを起動していくのだが、xdg-desktop-portal-wlr の systemd ユニットは起動時に WAYLAND_DISPLAY 環境変数をチェックするようになっている。このチェックは私の環境では通らなかったので、ユニットファイルを編集して環境変数を設定する。この際には、`cp /usr/lib/systemd/user/xdg-desktop-portal-wlr.service .config/systemd/user`して、コピーしたほうを編集すればよい。
```
[Unit]
Description=Portal service (wlroots implementation)
PartOf=graphical-session.target
After=graphical-session.target
ConditionEnvironment=WAYLAND_DISPLAY

[Service]
Type=dbus
BusName=org.freedesktop.impl.portal.desktop.wlr
ExecStart=/usr/libexec/xdg-desktop-portal-wlr
Restart=on-failure
```
これを、
```
[Unit]
Description=Portal service (wlroots implementation)
PartOf=graphical-session.target
After=graphical-session.target

[Service]
Type=dbus
BusName=org.freedesktop.impl.portal.desktop.wlr
ExecStart=/usr/libexec/xdg-desktop-portal-wlr
Restart=on-failure
Environment=WAYLAND_DISPLAY=wayland-1
```
こうした。`Environment=WAYLAND_DISPLAY=wayland-1`が追加されている。また`ConditionEnvironment=WAYLAND_DISPLAY`を消しているが不要かもしれない。

このあと`systemctl --user daemon-reload`すると、`systemctl --user status xdg-desktop-portal.service`で起動できる。xdg-desktop-portal と xdg-desktop-portal-wlr の両方に対して status を見て、きちんと起動しているか確認しておくこと。

これで、xdg-desktop-portal に対応しているアプリではスクリーン共有ができるようになるはずだ。

ちなみにこれらのサービスはFirefoxやOBSなどのアプリケーションより先に起動していなければならない。Sway の起動と同時に立ち上げるのが良いだろう。

###  余談
WAYLAND_DISPLAYのチェックは Flatpak のコンテナ内で動くことを想定しているのだろうか。環境変数を設定する方法として systemd set-environment コマンドもあるが、この変数が設定されていると今度は Sway の起動に失敗するので、ユーザーインスタンス全体に影響する方法は使えない。よって今回は仕方なくユニットファイルを直接編集することにした。

# 仮想カメラを使う
Waylandに対応していない不親切なアプリケーションで画面共有をするためには、追加で以下の手順が必要だ。

### v4l2loopbackのインストール
まず v4l2loopback をインストールする。鬼門だ。Arch Linuxなどであればdkmsで自動ビルドしてくれるパッケージがあるが、我らGentooユーザーは自前でやらなければならない。

なお、v4l2loopback のインストールはカーネルアップデートのたびに繰り返す必要がある。

まず、[v4l2loopback](https://github.com/umlaeute/v4l2loopback)をcloneないしpullしてくる。

次にクローンしてきたリポジトリ内でmakeを実行する。これを成功させるためには、`/lib/modules/$(uname -r)/build`が正しいパスへのリンクになっている必要がある。またそれだけでなく、その中に.configやModule.symversがなければならない。カーネルをビルドするときに一緒にv4l2loopbackのビルドもしてしまうのが楽だろう。

最後に、make install で完了。

### 仮想カメラを作る
Wayland から仮想カメラへのアダプタとして、ここでは OBS Studio を使うことにする。これらの USE フラグを有効にしてインストールする。
```
media-video/obs-studio pipewire v4l wayland
```
OBS を起動する前に、必要なサービス(xdg-desktop-portal{-wlr})が起動していることを確かめる。また、以下のコマンドで v4l2loopback モジュールも読み込んでおく。
```
modprobe -iv v4l2loopback
```
次に OBS を立ち上げる。
画面下部に Sources と名のついた領域があるはずだ。そこの+ボタンから、Screen Capture (Pipewire) を選択する。この選択肢がない場合、正しく設定ができていない。xdg-desktop-portal(-wlr)が正しく起動しているか、またPipewireサポート付きでビルドされているか確かめよう。  
無事 Sources に追加されたら、これをダブルクリックして開くウィンドウからどのモニターをキャプチャするか選択できる。  
その後右下の Start Virtual Camera を有効にすればようやく仮想カメラが準備される。  
カメラを使うアプリケーションから、Dummy Device のような名前のカメラが見えるはずなので、それを選択すると画面共有ができる。

## ところで
Zoom の Linux クライアントがクラッシュして動かない。せっかく画面共有ができるようになったのになぁ。

