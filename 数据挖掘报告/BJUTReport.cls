% Adapted from an existing LaTeX thesis template for a Beijing University of Technology course report.
% License: LaTeX Project Public License v1.3c


\ProvidesClass{BJUTReport}[2026/05/06 v0.1 Course report class for BJUT]
\NeedsTeXFormat{LaTeX2e}

\RequirePackage{kvoptions}
\RequirePackage{etoolbox}
\RequirePackage{calc}

\SetupKeyvalOptions{family=CUC, prefix=CUC@, setkeys=\kvsetkeys}
\newcommand{\ckv}[1]{\kvsetkeys{CUC}{#1}}

\DeclareDefaultOption{\PassOptionsToClass{\CurrentOption}{article}}
\ProcessKeyvalOptions*\relax
\LoadClass{article}

% 设置纸张格式
\RequirePackage[
  a4paper,
  left=2.4cm,right=2.4cm,top=2.4cm,bottom=2.4cm,%页面设置：页边距上下左右各用2.4cm。
  headsep=0.3cm]{geometry}
\setlength{\headsep}{0.6cm}

\RequirePackage{amsthm,amsmath,amssymb,indentfirst,booktabs,multicol,multirow,xcolor,graphicx,fancyhdr,hologo,array,hyperref}

% 设置目录与引用的超链接（需要编译多次）
\RequirePackage{hyperref}
\hypersetup{
  pdfborder={0 0 0},
  colorlinks=false,linkcolor={blue},urlcolor={blue},filecolor={blue},citecolor={blue},
  linktoc=all,
}

%%%%%%%%%%%%%%%%%%%%%% 字体与段落 %%%%%%%%%%%%%%%%%%%%%%

\PassOptionsToPackage{no-math}{fontspec}
\RequirePackage[UTF8,scheme=plain]{ctex}
\setmainfont{Times New Roman}       %西文字体默认


% 1.5倍行距
\linespread{1.5}

% 段落缩进2字符
\setlength\parindent{2\ccwd}

%%%%%%%%%%%%%%%%%%%%%% 引用格式 %%%%%%%%%%%%%%%%%%%%%% 参考文献样式设置
\RequirePackage[authoryear]{natbib} % 启用作者-年份格式
\RequirePackage{gbt7714}    %用于生成符合中国国家标准 GB/T 7714-2015 的参考文献样式。
\bibliographystyle{gbt7714-author-year}   %作者-年份制，自动实现中文文献在前，外文文献在后的排序

% 自定义"等"的翻译
\AtBeginDocument{\renewcommand{\harvardand}{等}} % 中文"等"替代"and"

% 统一使用英文逗号格式的引用
% gbt7714的bst会在.bbl中为中文条目自动使用中文逗号
% 修改natbib分隔符：统一使用英文逗号
\AtBeginDocument{%
  \renewcommand{\NAT@sep}{,}% 作者与年份之间使用英文逗号
  \renewcommand{\NAT@aysep}{,}% 作者-年份引用中使用英文逗号
}

% 将\cite命令重定义为\citep，实现(作者,年份)格式
\let\cite\citep

\setlength{\bibsep}{0pt}              %文献条目之间的垂直间距为 0
\def\bibfont{\songti\zihao{-4}}        %参考文献字体：中文宋体，西文Times New Roman，小四号
% 设置参考文献悬挂缩进2字距
\setlength{\bibhang}{2\ccwd}           % 设置悬挂缩进为2个中文字符宽度

% 自定义参考文献标题：黑体、四号、居中、字间距1字距、段前0行、段后0行、1.5倍行距
\renewcommand{\refname}{%
  \centering\heiti\zihao{4}参\hspace{\ccwd}考\hspace{\ccwd}文\hspace{\ccwd}献%
  \par\nobreak%
    \vspace{-0.6cm} % 段后间距为0行
}
\renewcommand\figurename{图}
\renewcommand\tablename{表}
\renewcommand{\theequation}{式\arabic{equation}} % 公式编号格式：（式1）（式2）...

\RequirePackage{caption}
\DeclareCaptionLabelSeparator{oneccwd}{\hspace{1\ccwd}}
\captionsetup[table]{skip=8pt,labelsep=oneccwd}
\captionsetup[figure]{skip=8pt,labelsep=oneccwd}

\renewcommand{\captionfont}{\songti\zihao{5}}


%\usepackage{booktabs} % 用于美化表格
%\usepackage{float} % 用于控制表格位置
%% 设置表注格式
%\newcommand{\tablesource}[1]{%
%  \vspace{4pt} % 表题与表注之间的间距
% \parbox{\linewidth}{\songti\zihao{-5}\linespread{1.5}\selectfont #1} % 表注字体为宋体，小五号，1.5倍行距
%}

\usepackage{booktabs}
\usepackage{float}

% ------------------
% 表格 三套间距（完全生效）
% ------------------
\captionsetup[table]{
  skip=4pt,     % 表题 ↔ 表格 之间的距离（你要多少改多少）
  position=above % 表题在表格上方
}

% 表注命令（表格 ↔ 表注 间距 固定生效）
\newcommand{\tablesource}[1]{%
  \par
  \vspace{6pt}   % 表格 ↔ 表注 之间的距离
  \noindent
  \parbox{\linewidth}{%
    \songti\zihao{-5}\linespread{1.5}\selectfont #1%
  }%
  \par
}

% 设置图题格式
\renewcommand{\figurename}{图} % 图编号前缀
\DeclareCaptionLabelSeparator{oneccwd}{\hspace{1\ccwd}}
% 设置图题格式
\captionsetup[figure]{
  labelsep=oneccwd, % 使用自定义分隔符 onespace
  font=small, % 图题字体为小号
  justification=centering % 图题居中
}

% 设置图注格式
\newcommand{\figsource}[1]{%
  \vspace{4pt} % 图题与图注之间的间距
  \parbox{\linewidth}{\songti\zihao{-5}\linespread{1.5}\selectfont #1} % 图注字体为宋体，小五号，1.5倍行距
}


% 设置插图与正文之间的间距
\setlength{\intextsep}{12pt} % 插图与正文之间上下各空一行


%%%%%%%%%%%%%%%%%%%%%% code style %%%%%%%%%%%%%%%%%%%%%%

\RequirePackage{listings}

\definecolor{codegreen}{rgb}{0,0.6,0}
\definecolor{codegray}{rgb}{0.5,0.5,0.5}
\definecolor{codepurple}{rgb}{0.58,0,0.82}

\lstdefinestyle{defaultstyle}{
    commentstyle=\color{codegreen},
    keywordstyle=\color{magenta},
    numberstyle=\tiny\color{codegray},
    stringstyle=\color{codepurple},
    basicstyle=\ttfamily\footnotesize,
    breaklines=true,
    keepspaces=true,
    tabsize=2,
    frame=single,
}

\lstset{style=defaultstyle}

%%%%%%%%%%%%%%%%%%%%%% 原创声明接口定义 %%%%%%%%%%%%%%%%%%%%%%
% 定义用户接口命令，用于接收 .tex 文件传入的参数
\newcommand{\signauthor}[1]{\def\@signauthor{#1}}
\newcommand{\signsupervisor}[1]{\def\@signsupervisor{#1}}
\newcommand{\signyear}[1]{\def\@signyear{#1}}
\newcommand{\signmonth}[1]{\def\@signmonth{#1}}
\newcommand{\signday}[1]{\def\@signday{#1}}

% 初始化默认值（防止用户在 .tex 中漏填导致报错）
\def\@signauthor{}
\def\@signsupervisor{}
\def\@signyear{}
\def\@signmonth{}
\def\@signday{}

%%%%%%%%%%%%%%%%%%%%%% 原创声明环境定义 %%%%%%%%%%%%%%%%%%%%%%
\newenvironment{authorization}{
\setlength{\parindent}{2\ccwd}  % 设置段首缩进为 2 个中文字符宽度

\thispagestyle{empty} % 本页不显示页码
\addtocounter{page}{-1} % 将页码计数器减 1

    \begin{center}
        \textbf{\Large 北京工业大学课程报告原创性声明}
    \end{center}

    本人郑重声明：所呈交的课程报告，是本人在教师的指导下，独立进行研究和分析工作所取得的成果。除文中已经注明引用的内容外，本报告不包含任何其他个人或集体已经发表或撰写过的作品成果。对本文研究和实现做出重要贡献的个人和集体，均已在文中以明确方式标明。本人完全意识到本声明的法律结果由本人承担。

    \vspace{1cm}
    \noindent
    % 这里使用 \@signauthor 等内部变量自动填充，保留了下划线和固定宽度对齐
    作者签名： \underline{\makebox[3cm]{\@signauthor}} \hfill 日期： \underline{\makebox[2cm]{\@signyear}} 年 \underline{\makebox[1cm]{\@signmonth}} 月 \underline{\makebox[1cm]{\@signday}} 日 \hfill

    \vspace{5cm}

    \begin{center}
        \textbf{\Large 北京工业大学课程报告使用授权声明}
    \end{center}
    \setlength{\parindent}{2\ccwd}

    本人完全了解学校有关保留、使用课程报告的规定，同意学校保留并向有关部门或机构送交课程报告的复印件和电子版，允许课程报告被查阅和借阅。学校可以将本课程报告的全部或部分内容编入有关数据库进行检索，可以采用影印、缩印或扫描等复制手段保存和汇编课程报告。

    \vspace{1cm}

    \noindent
    % 同样使用内部变量填充作者、导师和日期
    作者签名： \underline{\makebox[3cm]{\@signauthor}} \hfill  指导教师签名：\underline{\makebox[3cm]{\@signsupervisor}}\\
    \vspace{0.2cm}
    日期： \underline{\makebox[2cm]{\@signyear}} 年 \underline{\makebox[1cm]{\@signmonth}} 月 \underline{\makebox[1cm]{\@signday}} 日 \hfill 日期： \underline{\makebox[2cm]{\@signyear}} 年 \underline{\makebox[1cm]{\@signmonth}} 月 \underline{\makebox[1cm]{\@signday}} 日
}{}


%%%%%%%%%%%%%%%%%%%%%%%%%%% 摘要与关键词%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% 中文摘要命令
\renewenvironment{abstract} {
\clearpage \phantomsection
\pagenumbering{Roman} % 从摘要开始使用罗马数字页码
\begin{center}
    \zihao{4} \heiti 摘 \qquad \qquad 要 % 标题中间空4个字距

\vspace{8pt}
\end{center}
% \addcontentsline{toc}{section}{摘 \quad 要} % 不添加到目录
\zihao{-4} \ignorespaces\indent  % 添加段首缩进

} { \clearpage }


\newcommand{\keywords}[1]{\newline\newline\newline\noindent\heiti{关键词：}\songti\zihao{-4} #1}



% 英文摘要环境（完美修复版）
\newenvironment{abstractEN}[4]{%
    \clearpage
    \phantomsection
    \begin{center}
        {\textbf{\large #1}} \\[1ex]
        #2 \\[1ex]
        （#3, Beijing University of Technology, Beijing 100124, China）
    \end{center}
    \vspace{2ex} % 标题区域与正文之间增加一点呼吸空间
    \noindent\textbf{Abstract: } #4%
}


% 英文关键词命令
\newcommand{\keywordsEN}[1]{%
    \par\vspace{1cm} % 使用 \par 确保前一个段落结束，再加空距
    \noindent\textbf{Key words: } #1%
    \clearpage % 在关键词之后换页
}

%%%%%%%%%%%%%%%%%%%%%% 章节标题样式 %%%%%%%%%%%%%%%%%%%%%%

\RequirePackage{setspace,titlesec,zhnumber,titletoc}

% 修改章节编号格式
\renewcommand{\thesection}{\arabic{section}} % 一级标题：1, 2, 3
\renewcommand{\thesubsection}{\thesection.\arabic{subsection}} % 二级标题：1.1, 1.2
\renewcommand{\thesubsubsection}{\thesubsection.\arabic{subsubsection}} % 三级标题：1.1.1, 1.1.2
\renewcommand{\theparagraph}{\thesubsubsection.\arabic{paragraph}} % 四级标题：1.1.1.1, 1.1.1.2

\newcommand{\sectionbreak}{\clearpage} % 每章节清页面



% 一级标题格式
% 修改点：将原来的 {\thesection~~}{0pt} 改为 {\thesection}{\ccwd}
% \ccwd 代表一个当前汉字的宽度，保证间距固定
\titleformat{\section}[block]{\zihao{4} \heiti}
{\thesection}{\ccwd}{\vspace{0pt}}

% 二级标题格式
\titleformat{\subsection}{\zihao{-4} \heiti}
{\thesubsection}{\ccwd}{}

% 三级标题格式：改为楷体
\titleformat{\subsubsection}{\zihao{-4} \kaishu}
{\thesubsubsection}{\ccwd}{}

% 四级标题格式：改为楷体
\titleformat{\paragraph}[block]{\zihao{-4} \kaishu}
{\theparagraph~~}{0pt}{}

\setcounter{secnumdepth}{4} % 设置标题编号深度为 4（包括 paragraph）

% 设置所有标题的段前间距和段后间距均为 0 行
% 语法：\titlespacing*{<命令>}{<左间距>}{<段前间距>}{<段后间距>}
\titlespacing*{\section}{0pt}{0pt}{0pt}    % 一级标题：段前0行，段后0行
\titlespacing*{\subsection}{0pt}{0pt}{0pt} % 二级标题：段前0行，段后0行
\titlespacing*{\subsubsection}{0pt}{0pt}{0pt} % 三级标题：段前0行，段后0行
\titlespacing*{\paragraph}{0pt}{0pt}{0pt}  % 四级标题：段前0行，段后0行


%%%%%%%%%%%%%%%%%%%%%% 目录样式 %%%%%%%%%%%%%%%%%%%%%%
% 定义目录标题格式
\renewcommand\contentsname{%
  \vspace*{-1.8cm}  % 与上文间距2cm
  \makebox[\textwidth][c]{\heiti \zihao{-3} 目\qquad\qquad 录} % 目录标题居中，小三号字
  \vspace{18pt}  % 与下文间距18pt，相当于1.5倍行距距离（小四号字）
}

\titlecontents{section}[0pt]{\songti \zihao{-4}\linespread{1.5}\selectfont}
{\thecontentslabel\hspace{0.5em}}{}%
{\titlerule*[0.7em]{.}\contentspage}

\titlecontents{subsection}[0pt]{\songti \zihao{-4}\linespread{1.5}\selectfont}
{\thecontentslabel\hspace{0.5em}}{}%
{\titlerule*[0.7em]{.}\contentspage}

\titlecontents{subsubsection}[0pt]{\songti \zihao{-4}\linespread{1.5}\selectfont}
{\thecontentslabel\hspace{0.5em}}{}%
{\titlerule*[0.7em]{.}\contentspage}

\setcounter{tocdepth}{3} % 设置目录深度为 3（不显示 paragraph）


%%%%%%%%%%%%%%%%%%%%%% 命令封装 %%%%%%%%%%%%%%%%%%%%%%

% 定义参考文献环境
\newenvironment{references}{
    \clearpage
    \phantomsection
    \addcontentsline{toc}{section}{参考文献} % 添加到目录
    \refname % 调用自定义的参考文献标题
    \vspace{4pt} % 参考文献标题与文献列表之间的间距（约1行）
    \setstretch{1.5} % 1.5倍行距
}{
    \clearpage
}

\fancypagestyle{CUCThesisMain}{
    \fancyhf{}
    \cfoot{\songti\zihao{-5}{\thepage}}
    \renewcommand{\headrulewidth}{0pt}
}


\newcommand{\contentpage}{
  \begin{spacing}{1.5}
    \tableofcontents
  \end{spacing}

  \clearpage
  \pagenumbering{arabic} % 正文开始使用阿拉伯数字页码
  \setcounter{page}{1}
}

\newcommand{\nonumsection}[1]{
  \phantomsection
  \section*{#1}
  \stepcounter{section}
  \addcontentsline{toc}{section}{#1}
}





%%%%%%%%%%%%%%%%%%%%%% 封面 %%%%%%%%%%%%%%%%%%%%%%

\newcommand{\dunderline}[3][-6pt]{{
  \setbox0=\hbox{#3}
  % 将内容 #3 放入一个盒子中
  \ooalign{\copy0\cr\rule[\dimexpr#1-#2\relax]{\wd0}{#2}}
  % 使用 `\ooalign` 在内容下方绘制一条线：
  % `\copy0` 复制盒子中的内容
  % `\rule` 绘制一条水平线，线的位置由 `#1` 和 `#2` 控制，宽度为盒子的宽度
}}
% 定义一个名为 `dunderline` 的命令，用于在文本下方添加下划线
% 参数：
% `#1` 可选参数，默认值为 -6pt，控制下划线的垂直位置
% `#2` 必选参数，控制下划线的粗细
% `#3` 必选参数，需要添加下划线的文本

\newcommand{\infobox}[2]{
    \hspace{2.4cm}\heiti\zihao{-2}\textbf{\selectfont{#1~\dunderline{1pt}{\makebox[8cm][c]{\mdseries #2}}}}
}

\newcommand{\trbox}[2]{
\hspace{2.4cm}\heiti\zihao{-2}\textbf{\selectfont{#1~\dunderline{1pt}{\makebox[3.2cm][c]{\mdseries #2}}}}
}
\newcommand{\jobbox}[2]{
\hspace{2.4cm}\heiti\zihao{-2}\textbf{\selectfont{#1~\dunderline{1pt}{\makebox[2.8cm][c]{\mdseries #2}}}}
}

\newcommand{\coverpage}{
  \begin{titlepage}
    \vspace*{-10pt}
    % 向上移动 10pt，调整页面顶部间距

    \vspace*{2\ccwd}
    % 添加 2 个汉字宽度的垂直间距

    \centering
    {\zihao{-0}\heiti 北京工业大学}
    \vspace{0.8cm}

    \centering
    \zihao{-0}\textbf{\songti{数据挖掘课程报告}}
    % 设置标题为"数据挖掘课程报告"，字体为小初号宋体加粗
    \vspace{1cm}
    % 添加 0.6cm 的垂直间距

    \zihao{2}\textbf{\heiti\thesisTitle}
    % 设置论文标题，字体为二号黑体加粗
    \vspace{4.5cm}
    % 添加 2.5cm 的垂直间距

     \flushleft  %左对齐
         \begin{spacing}{1.5}

 % 设置行距为 1.5 倍
        \infobox{ \zihao{-3}\songti{学\hphantom{空白}院:}}{\yourDept}
        % 生成"学院"信息框，内容为 `\yourDept`

        \infobox{ \zihao{-3}\songti{专\hphantom{空白}业:}}{\yourMajor}
        % 生成"专业"信息框，内容为 `\yourMajor`

        \infobox{ \zihao{-3}\songti{姓\hphantom{空白}名:}}{\yourName}
        % 生成"姓名"信息框，内容为 `\yourName`

        \infobox{ \zihao{-3}\songti{学\hphantom{空白}号:}}{\studentID}
        % 生成"学号"信息框，内容为 `\studentID`

    \makebox[0.45\textwidth][l]{\trbox{\zihao{-3}\songti{指导教师:}}{\yourMentor}}\hspace{-1.2cm}
    \makebox[0.45\textwidth][l]{\jobbox{\zihao{-3}\songti{职称:}}{\yourjob}}
        % 生成"职称"信息框，内容为 `\yourjob`
        % 生成"指导教师"信息框，内容为 `\yourMentor`

% 替换为：
\hspace{2.568cm}\heiti\zihao{-2}\textbf{\selectfont{\zihao{-3}\songti{提交日期:}~\dunderline{1pt}{\makebox[2.5cm][c]{\mdseries \yourYear}}~年~\dunderline{1pt}{\makebox[1.3cm][c]{\mdseries \yourMonth}}~月~\dunderline{1pt}{\makebox[1.3cm][c]{\mdseries \yourDay}}~日}}
        % 生成"提交日期"信息框，内容为 `\Date`
    \end{spacing}

    \vspace{3cm}
    % 添加 3cm 的垂直间距


  \end{titlepage}

  \pagestyle{CUCThesisMain}
  % 设置页面样式为 `CUCThesisMain`
}
% 定义一个名为 `coverpage` 的命令，用于生成论文封面


%%%%%%%%%%%%%%%%%%%%%% 编程语言语法高亮支持 %%%%%%%%%%%%%%%%%%%%%%

\usepackage{color}
\definecolor{lightgray}{rgb}{.9,.9,.9}
\definecolor{darkgray}{rgb}{.4,.4,.4}
\definecolor{purple}{rgb}{0.65, 0.12, 0.82}
\definecolor{orange}{rgb}{0.9, 0.4, 0.0}

% ====================== JavaScript ======================
\lstdefinelanguage{JavaScript}{
  keywords={typeof, new, true, false, catch, function, return, null, switch, var, if, in, while, do, else, case, break, const},
  keywordstyle=\color{blue}\bfseries,
  ndkeywords={class, export, boolean, throw, implements, import, this, async},
  ndkeywordstyle=\color{darkgray}\bfseries,
  identifierstyle=\color{black},
  sensitive=false,
  comment=[l]{//},
  morecomment=[s]{/*}{*/},
  commentstyle=\color{purple}\ttfamily,
  stringstyle=\color{red}\ttfamily,
  morestring=[b]',
  morestring=[b]"
}

% ====================== Python ======================
\lstdefinelanguage{Python}{
  keywords={and, as, assert, break, class, continue, def, del, elif, else, except, False, finally, for, from, global, if, import, in, is, lambda, None, nonlocal, not, or, pass, raise, return, True, try, while, with, yield},
  keywordstyle=\color{blue}\bfseries,
  ndkeywords={self, print, range, len, input, int, str, list, dict, set, tuple},
  ndkeywordstyle=\color{orange}\bfseries,
  identifierstyle=\color{black},
  sensitive=true,
  comment=[l]{\#},
  commentstyle=\color{purple}\ttfamily,
  stringstyle=\color{red}\ttfamily,
  morestring=[b]",
  morestring=[b]'
}

% ====================== C ======================
\lstdefinelanguage{C}{
  keywords={auto, break, case, char, const, continue, default, do, double, else, enum, extern, float, for, goto, if, inline, int, long, register, restrict, return, short, signed, sizeof, static, struct, switch, typedef, union, unsigned, void, volatile, while, _Alignas, _Alignof, _Atomic, _Bool, _Complex, _Generic, _Imaginary, _Noreturn, _Static_assert, _Thread_local},
  keywordstyle=\color{blue}\bfseries,
  ndkeywords={printf, scanf, main, include, define, malloc, free, NULL},
  ndkeywordstyle=\color{darkgray}\bfseries,
  identifierstyle=\color{black},
  sensitive=true,
  comment=[l]{//},
  morecomment=[s]{/*}{*/},
  commentstyle=\color{purple}\ttfamily,
  stringstyle=\color{red}\ttfamily,
  morestring=[b]",
  morestring=[b]'
}

% ====================== C++ ======================
\lstdefinelanguage{C++}{
  keywords={alignas, alignof, and, and_eq, asm, atomic_cancel, atomic_commit, atomic_noexcept, auto, bitand, bitor, bool, break, case, catch, char, char8_t, char16_t, char32_t, class, co_await, co_return, co_yield, complex, const, const_cast, constexpr, consteval, consexpr, continue, decltype, default, delete, do, double, dynamic_cast, else, enum, explicit, export, extern, false, float, for, friend, goto, if, import, inline, int, long, module, mutable, namespace, new, noexcept, not, not_eq, nullptr, operator, or, or_eq, private, protected, public, ref, register, reinterpret_cast, requires, return, short, signed, sizeof, static, static_assert, static_cast, struct, switch, synchronized, template, this, thread_local, throw, true, try, typeid, typename, union, unsigned, using, virtual, void, volatile, wchar_t, while, xor, xor_eq},
  keywordstyle=\color{blue}\bfseries,
  ndkeywords={std, string, vector, map, cout, cin, endl, namespace, include, define},
  ndkeywordstyle=\color{orange}\bfseries,
  identifierstyle=\color{black},
  sensitive=true,
  comment=[l]{//},
  morecomment=[s]{/*}{*/},
  commentstyle=\color{purple}\ttfamily,
  stringstyle=\color{red}\ttfamily,
  morestring=[b]",
  morestring=[b]'
}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%附录设定%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 定义附录格式
\RequirePackage{hyperref}
\renewcommand{\appendix}{%
  \par
  \setcounter{section}{0} % 重置章节计数器

  % 设置附录的目录深度为 1（只显示附录主标题，不显示 subsection 及以下级别）
  \addtocontents{toc}{\protect\setcounter{tocdepth}{1}}

  % 定义附录专用的超链接目标格式
  \renewcommand{\theHsection}{appendix.\arabic{section}}

  % 只修改一级标题的格式
  \renewcommand{\thesection}{附录\ \Alph{section}}

  % 子标题保持原有的数字格式
  \renewcommand{\thesubsection}{\arabic{subsection}}
  \renewcommand{\thesubsubsection}{\arabic{subsection}.\arabic{subsubsection}}
  \renewcommand{\theparagraph}{\arabic{subsection}.\arabic{subsubsection}.\arabic{paragraph}}

  % 为每个附录节添加超链接锚点
  \titleformat{\section}[block]
    {\clearpage\phantomsection
     \vspace{12pt} % 正文与附录之间的间距（约1行）
     \zihao{4}\heiti\centering}
    {\thesection}{1em}{\vspace{12pt}} % 附录标题与内容之间的间距（约1行）

\titlespacing*{\section}{0pt}{0pt}{0pt} % 附录标题段前0行，段后0行
  % 重置各类计数器
  \setcounter{figure}{0}
  \setcounter{table}{0}
  \setcounter{equation}{0}

  % 修改图表公式编号格式：图A1、表A1、式A1
  \renewcommand{\thefigure}{\Alph{section}\arabic{figure}}
  \renewcommand{\thetable}{\Alph{section}\arabic{table}}
  \renewcommand{\theequation}{式\Alph{section}\arabic{equation}} % 附录公式编号格式：（式A1）（式A2）...
}


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%致谢%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% 定义致谢内容格式
\newenvironment{acknowledgement}{%
  \clearpage\addcontentsline{toc}{section}{致谢} % 将“致谢”加入目录（大纲级别1级）
  \centering\heiti\zihao{4}致\hspace{4\ccwd}谢\par\nobreak % 致谢标题：黑体、四号、居中、字间距4字距
  \vspace{12pt} % 标题与内容之间的间距
  \justify % 两端对齐
  \songti\zihao{-4} % 中文字体宋体，小四号
  \setmainfont{Times New Roman} % 西文字体Times New Roman
  \setlength{\parindent}{2\ccwd} % 首行缩进2字距
  \setstretch{1.5} % 1.5倍行距
  \setlength{\parskip}{0pt} % 段落间距为0

}{%
  \par
}



%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%脚注%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\RequirePackage{pifont}
\renewcommand{\thefootnote}{\ding{\numexpr171+\value{footnote}}}
\usepackage{ragged2e}

% 设置脚注格式
\usepackage{footmisc}
\renewcommand{\footnotelayout}{%
  \fontsize{9}{1}\selectfont % 小五号字体，行距为 11pt（单倍行距）
  \setlength{\parindent}{0pt} % 无缩进
  \setlength{\parskip}{0pt} % 段前0行，段后0行
  \justifying % 两端对齐
}

% 确保脚注全文连续编号
\setcounter{footnote}{0} % 重置脚注计数器
