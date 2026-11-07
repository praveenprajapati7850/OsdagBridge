# =============================================================================
# OsdagBridge — Centralized Report Styling & Layout Module
# Defines theme colors, LaTeX typography, header/footer configuration,
# multipage table templates, and Matplotlib chart styling.
# =============================================================================

from typing import List, Optional
from osdagbridge.core.reports.report_utils import _tex

# ── Color Palette ─────────────────────────────────────────────────────────────
COLOR_OSDAG_GREEN = "#91B014"
COLOR_OSDAG_GREEN_TEX = "91B014"
COLOR_PASS = "#2E7D32"
COLOR_WARN = "#F57F17"
COLOR_FAIL = "#D32F2F"
COLOR_BAR_STEEL = "#2B5797"
COLOR_BAR_CONCRETE = "#607D8B"
COLOR_BAR_REBAR = "#FF8F00"
COLOR_REF_LINE = "#D32F2F"
COLOR_GRID = "#E0E0E0"
COLOR_TEXT = "#212121"

# ── LaTeX Document Preamble ───────────────────────────────────────────────────

def get_latex_preamble(project_name: str, job_number: str, report_date: str, report_version: str = "Rev 0") -> str:
    """Generate the full LaTeX preamble with fixed geometry, typography, and footers."""
    pn = _tex(project_name)
    jn = _tex(job_number)
    rd = _tex(report_date)
    rv = _tex(report_version)

    return r"""
\documentclass[12pt,a4paper]{report}

% Page Geometry & Margins (adjusted to prevent header/footer overlap)
\usepackage[
  a4paper,
  left=1in,
  right=1in,
  top=1.1in,
  bottom=1.1in,
  headheight=18pt,
  headsep=18pt,
  footskip=38pt
]{geometry}

\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{booktabs}
\usepackage{array}
\usepackage{tabularx}
\usepackage{float}
\usepackage{fancyhdr}
\usepackage[hidelinks]{hyperref}
\usepackage{xcolor}
\usepackage{setspace}
\usepackage{enumitem}
\usepackage{caption}

\captionsetup{
    labelfont=bf,
    justification=raggedright,
    singlelinecheck=false,
    format=plain,
    skip=4pt
}
\usepackage{subcaption}
\usepackage{multirow}
\usepackage{colortbl}
\usepackage{longtable}
\setlength{\LTleft}{\fill}
\setlength{\LTright}{\fill}
\usepackage{titlesec}
\usepackage{titletoc}
\usepackage{lastpage}
\usepackage{makecell}
\usepackage{etoolbox}
\usepackage{needspace}

\numberwithin{table}{chapter}
\numberwithin{figure}{chapter}

% Table layout, rules, and spacing
\setlength{\tabcolsep}{5pt}
\renewcommand{\arraystretch}{1.15}
\setlength{\LTpre}{4pt}
\setlength{\LTpost}{6pt}
\setlength{\arrayrulewidth}{0.5pt}
\setlength{\extrarowheight}{0.8pt}

% Prevent orphan table rows across page bottoms
\BeforeBeginEnvironment{table}{\needspace{5\baselineskip}}
\BeforeBeginEnvironment{longtable}{\needspace{5\baselineskip}}

\definecolor{osdagGreen}{HTML}{""" + COLOR_OSDAG_GREEN_TEX + r"""}
\definecolor{passGreen}{HTML}{2E7D32}
\definecolor{failRed}{HTML}{D32F2F}
\definecolor{warnAmber}{HTML}{F57F17}

% Headers and Footers with clean vertical positioning
\fancypagestyle{main}{
  \fancyhf{}
  \fancyhead[L]{\small\textbf{""" + pn + r"""} $|$ """ + jn + r"""}
  \fancyhead[R]{\small """ + rd + r""" $|$ """ + rv + r"""}
  \fancyfoot[L]{\footnotesize\textcolor{black!70}{Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay}}
  \fancyfoot[R]{\footnotesize\textbf{Page \thepage\ of \pageref{LastPage}}}
  \renewcommand{\headrule}{\color{osdagGreen}\hrule width\headwidth height 1.2pt \vspace{2pt}}
  \renewcommand{\footrule}{%
    \ifbool{hasSDonPage}{%
      \vspace{-16pt}%
      \hbox to \headwidth{\textcolor{black!80}{\scriptsize\textit{* Software default value}}\hfil}%
      \vspace{3pt}%
    }{%
      \vspace{-6pt}%
    }%
    \color{osdagGreen}\hrule width\headwidth height 1pt \vspace{5pt}%
  }
}

\fancypagestyle{plain}{
  \fancyhf{}
  \fancyhead[L]{\small\textbf{""" + pn + r"""} $|$ """ + jn + r"""}
  \fancyhead[R]{\small """ + rd + r""" $|$ """ + rv + r"""}
  \fancyfoot[L]{\footnotesize\textcolor{black!70}{Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay}}
  \fancyfoot[R]{\footnotesize\textbf{Page \thepage\ of \pageref{LastPage}}}
  \renewcommand{\headrule}{\color{osdagGreen}\hrule width\headwidth height 1.2pt \vspace{2pt}}
  \renewcommand{\footrule}{%
    \ifbool{hasSDonPage}{%
      \vspace{-16pt}%
      \hbox to \headwidth{\textcolor{black!80}{\scriptsize\textit{* Software default value}}\hfil}%
      \vspace{3pt}%
    }{%
      \vspace{-6pt}%
    }%
    \color{osdagGreen}\hrule width\headwidth height 1pt \vspace{5pt}%
  }
}

\fancypagestyle{firstpage}{
  \fancyhf{}
  \renewcommand{\headrulewidth}{0pt}
  \fancyfoot[L]{\footnotesize\textcolor{black!70}{Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay}}
  \fancyfoot[R]{\footnotesize\textbf{Page \thepage\ of \pageref{LastPage}}}
  \renewcommand{\footrule}{\vspace{-6pt}\color{osdagGreen}\hrule width\headwidth height 1pt \vspace{5pt}}
}

\pagestyle{main}
\setstretch{1.15}

% Column Type Definitions
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\newcolumntype{C}[1]{>{\centering\arraybackslash}p{#1}}
\newcolumntype{R}[1]{>{\raggedleft\arraybackslash}p{#1}}

% Software-default tracking macro
\newcommand{\placeholder}[1]{\textit{\textless #1\textgreater}}
\newcommand{\todo}[1]{\colorbox{yellow}{TODO: #1}}
\newbool{hasSDonPage}
\boolfalse{hasSDonPage}
\newcommand{\markSD}{\global\booltrue{hasSDonPage}}
\newcommand{\sdstar}{\textsuperscript{*}\markSD{}}
\AddToHook{shipout/before}{\global\boolfalse{hasSDonPage}}

\title{\Large\textbf{OsdagBridge} \\ \normalsize Open Source Software for Steel Girder Bridge Design \\ \vspace{2cm} \large Design Report}
\author{}
\date{}

\begin{document}
"""


# ── Longtable Repeated Header Helper ──────────────────────────────────────────

def build_multipage_table_header(
    col_spec: str,
    headers: List[str],
    caption: str,
    label: Optional[str] = None
) -> str:
    """
    Constructs standard LaTeX for a longtable with repeated headers on every page.
    Includes first head, continued table caption on subsequent pages,
    and footer continuation notes.
    """
    header_row = " & ".join(f"\\textbf{{{h}}}" for h in headers) + r" \\[5pt]"
    label_tex = f"\\label{{{label}}}" if label else ""
    num_cols = len(headers)

    return f"""\\begin{{longtable}}{{{col_spec}}}
\\caption{{\\textbf{{{caption}}}}}{label_tex} \\\\
\\hline
{header_row}
\\hline
\\endfirsthead

\\multicolumn{{{num_cols}}}{{c}}{{\\small\\textit{{(Table {caption} --- Continued from previous page)}}}} \\\\[4pt]
\\hline
{header_row}
\\hline
\\endhead

\\hline
\\multicolumn{{{num_cols}}}{{r}}{{\\scriptsize\\textit{{Continued on next page\\dots}}}} \\\\[2pt]
\\endfoot

\\hline
\\endlastfoot
"""


# ── Matplotlib Theming Helper ────────────────────────────────────────────────

def apply_chart_theme(plt_module, figsize=(7.0, 3.8)):
    """Configure matplotlib with a clean styling matching the LaTeX report."""
    plt = plt_module
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
        "font.size": 9.5,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.labelsize": 9.5,
        "axes.labelweight": "bold",
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "legend.fontsize": 8.5,
        "figure.titlesize": 12,
        "figure.titleweight": "bold",
        "figure.dpi": 200,
        "savefig.dpi": 200,
        "figure.autolayout": True,
        "axes.grid": True,
        "grid.color": COLOR_GRID,
        "grid.linestyle": "--",
        "grid.linewidth": 0.6,
        "grid.alpha": 0.7,
        "axes.edgecolor": "#CCCCCC",
        "axes.linewidth": 0.8,
    })
    fig, ax = plt.subplots(figsize=figsize)
    return fig, ax

