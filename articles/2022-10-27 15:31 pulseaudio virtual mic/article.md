# PulseAudioで仮想マイクを作る
## 仮想スピーカーを作る
仮想スピーカーを作れば勝手にそれのモニターソースが作られるので、それを利用する。
```
pactl load-module module-null-sink sink_name=Virtual-Speaker sink_properties=device.description=Virtual-Speaker
```
## 動作確認
適当なオーディオファイルを用意  
ターミナルを2つ開き、1つ目で以下を実行
```
parec --file-format=wav --device=Virtual-Speaker.monitor /path/to/saved-audio.wav
```
もう片方で以下を実行
```
paplay --device=Virtual-Speaker /path/to/sample-audio.wav
```

しばらく待って、saved-audio.wavにsample-audio.wavの内容が録音されていたら成功

## 後片付け
不要になったら以下の方法で削除できる
`pactl list short modules`でモジュール一覧を表示、`module-null-sink`の行の先頭にモジュール番号が記載されているので、以下のコマンドで削除
`pactl unload-module $MOD_NUM`
