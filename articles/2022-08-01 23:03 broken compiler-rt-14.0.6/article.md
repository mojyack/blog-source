## 今日も問題発生
いつものようにGentooをアプデすると、いつものようにコンパイルエラーが発生した。今回イかれたのは`sys-libs/compiler-rt-14.0.6`  だ。  
エラーの内容はこんな感じ
```
CMake Error at cmake/config-ix.cmake:208 (message):
  Please use architecture with 4 or 8 byte pointers.
Call Stack (most recent call first):
  CMakeLists.txt:251 (include)
```
リンクエラーとかならお茶の子さいさいだが、これはちょっとややこしそうだ。  
でもアップデートをサボることはできないので、貴重な時間をこんなことに費やすことに疑問を抱きながら、解決策を探していこう。

## CMakeをトレースしてみる
まず`config-ix.cmake`とやらを見に行こう。そこにはこう書いてある。
```
...
if (NOT CMAKE_SIZEOF_VOID_P EQUAL 4 AND
    NOT CMAKE_SIZEOF_VOID_P EQUAL 8)
    message(FATAL_ERROR "Please use architecture with 4 or 8 byte pointers.")
endif()
...
```
どうやら、今回のエラーの原因は`CMAKE_SIZEOF_VOID_P`変数が正しく設定されていないことに起因するようだ。  
では、この変数はどこで設定されるべきなのだろうか。CMakeでは`variable_watch`関数を使うと、ある変数への読み書きをトレースできる。早速、CMakeLists.txtの頭に`variable_watch(CMAKE_SIZEOF_VOID_P)`と書いて、この変数へのアクセスを読んでみた。

が、ヒットしない。読み込みは行われているものの、書き込みは発生していなかった。前提条件となる変数が別にあるのかもしれない。

## ソースを読む
その変数を知るために、今度はCMakeのソースに`set(CMAKE_SIZEOF_VOID_P `でgrepをかけてみる。すると、`Modules/CMakeCCompiler.cmake.in`に気になる部分を発見した。
```
...
# Save compiler ABI information.
set(CMAKE_C_SIZEOF_DATA_PTR "@CMAKE_C_SIZEOF_DATA_PTR@")
set(CMAKE_C_COMPILER_ABI "@CMAKE_C_COMPILER_ABI@")
set(CMAKE_C_BYTE_ORDER "@CMAKE_C_BYTE_ORDER@")
set(CMAKE_C_LIBRARY_ARCHITECTURE "@CMAKE_C_LIBRARY_ARCHITECTURE@")

if(CMAKE_C_SIZEOF_DATA_PTR)
  set(CMAKE_SIZEOF_VOID_P "${CMAKE_C_SIZEOF_DATA_PTR}")
endif()
...
```
なるほど、`CMAKE_C_SIZEOF_DATA_PTR`がその変数らしい。先ほどと同様に`variable_watch`で探ってみよう。  
...  
とやってみたものの、やはりめぼしいものは見つからなかった。違う方向からのアプローチが必要だ。やれやれ。

## 解決策発見
今回は14.0.4から14.0.6へのアップデートであった。原因がこの間にあることは確かなので、その間のコミットを探っていく。  その中で僕が目をつけたのは、["add -nostartfiles to nolib_flags"](https://gitweb.gentoo.org/repo/gentoo.git/commit/sys-libs/compiler-rt?id=828d8bf14cac680b319b107412d1eda05661436f) である。
このコミットは`compiler-rt`がインストールされていない環境で`compiler-rt`をビルドできるようにするものだ。 `nostartfiles`、いかにも重大そうだし、これ以外にそれらしいコミットも見つからない。 

本当にこのコミットが原因なのか確かめるため、変更された`local nolib_flags=( -nodefaultlibs -nostartfiles -lc )`の部分から、`nostartfiles`を消してみた。そのうえで、コンパイルしてみよう。  
...  
通ってしまった。やはりこのコミットが原因だったようだ。この時点でモチベーションが半分くらいになってしまったが、根本的な問題がわかるなら調べておきたいのがプログラマーというものだ。経過した時間に絶望しながら調査を続ける。

## やっぱり`nostartfiles`
さて、上の状態だと`CMAKE_C_SIZEOF_DATA_PTR`に正しい数が入っているはずだ。トレースしてみよう。
```
CMake Debug Log at /usr/share/cmake/Modules/CMakeDetermineCompilerABI.cmake:117 (set):
  Variable "CMAKE_C_SIZEOF_DATA_PTR" was accessed using MODIFIED_ACCESS with
  value "8".
Call Stack (most recent call first):
  /usr/share/cmake/Modules/CMakeTestCCompiler.cmake:26 (CMAKE_DETERMINE_COMPILER_ABI)
  CMakeLists.txt:13 (project)
```
見つけた。`CMakeDetermineCompilerABI.cmake`がキモらしい。そこではこのような処理が行われている。
```
function(CMAKE_DETERMINE_COMPILER_ABI lang src)
...
    try_compile(CMAKE_${lang}_ABI_COMPILED
        ${CMAKE_BINARY_DIR} ${src}
        CMAKE_FLAGS ${CMAKE_FLAGS}
                    # Ignore unused flags when we are just determining the ABI.
                    "--no-warn-unused-cli"
        COMPILE_DEFINITIONS ${COMPILE_DEFINITIONS}
        OUTPUT_VARIABLE OUTPUT
        COPY_FILE "${BIN}"
        COPY_FILE_ERROR _copy_error
        __CMAKE_INTERNAL ABI
    )
...
    if(CMAKE_${lang}_ABI_COMPILED)
....
        set(CMAKE_${lang}_SIZEOF_DATA_PTR "${ABI_SIZEOF_DPTR}" PARENT_SCOPE)
....
```
要するに、かんたんなプログラムをコンパイルして、その出力から処理系のバイトオーダーやポインタサイズを取得しているようだ。  
`nostartfiles`をつけたり消したりしながらこのあたりの変数を眺めていると、ある出力が目に止まった。
```
ld.lld: warning: cannot find entry symbol _start; not setting start address
```
これは、`nostartfiles`がついている状態で`OUTPUT`変数に含まれていたものである。なるほど、これでは実行できるわけもない。ここに今回の問題の原因が明らかになった。

## まとめ
今回の問題は、`nostartfiles`フラグの追加によりビルドシステムが使うプログラムが起動できなくなり、必要な情報が収集できなくなったことに起因するものだった。これでは、面倒だが、ebuildファイルを独自に編集して使うしかないだろう。

不思議なのは、なぜ自分の環境だけこんなことが起こったのかである。このebuildはすでにstableにマークされているので、メンテナの環境では問題がなかったはずだ。また、執筆時点でこのコミットからは10日ほど経過しており、その間特にissueなども立っていないため、多分その他の人も大丈夫だったのだろう。  
今回の調査で問題が発生している部分は特定できたが、なぜそこが原因となっているかまではわからなかった。謎は残るが、一日は無限ではない。これの解明は将来の自分に託して、今日は切り上げることにする。  
早くmusl/clang/systemdの環境がGentooで公式にサポートされる時代が来てほしいものだ。
