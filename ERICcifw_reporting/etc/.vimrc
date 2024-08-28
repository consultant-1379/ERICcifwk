au BufEnter *.rc exe "set syntax=sh"
au BufEnter *.d setf dtrace
syntax enable
" set autoindent
"

set ls=2
set tabstop=4
set shiftwidth=4
set smartindent
set cindent
set autoindent
set showcmd
"set hlsearch
set incsearch
set hlsearch
set ruler
"set visualbell t_vb=
set novisualbell
"set number
set title
set ttyfast
"set nowrap

" Don't use tab characters in files
set expandtab

syntax on

filetype plugin indent on
autocmd FileType text setlocal textwidth=78
"au BufEnter *.rc exe "set syntax=sh"

au BufEnter *.ddl exe "set syntax=sql"

function! s:insert_gates()
        let gatename = substitute(toupper(expand("%:t")), "\\.", "_", "g")
        execute "normal i#ifndef " . gatename
        execute "normal o#define " . gatename . "   "
        execute "normal Go#endif /* " . gatename . " */"
        normal kk
endfunction

autocmd  BufNewFile *.{h,hpp} call <SID>insert_gates()

" automatically give executable permissions if filename is *.sh
" au BufWritePost *.sh :!chmod a+x <afile>
" automatically insert "#!/bin/sh" line for *.sh files
au BufEnter *.sh if getline(1) == "" | silent :call setline(1, "#!/bin/bash") | endif
" automatically give executable permissions if file begins with #!/bin/sh
au BufWritePost * if getline(1) =~ "^#!/bin/[a-z]*sh" | silent :!chmod a+x %
au BufWritePost * | endif
" COLOURS ...
" set guifont=-monotype-couriernew-medium-r-normal--0-0-0-0-m-0-iso8859-8
set guifont=screen
set backspace=indent,eol,start
" I like this scheme
:colorscheme delek
" Change the status line to something more palateable
"hi StatusLine     term=bold cterm=bold ctermfg=white ctermbg=darkblue gui=bold guifg=blue guibg=white
" Highlight whitespace at the end of lines
"highlight WhitespaceEOL ctermbg=red guibg=red
"match WhitespaceEOL /\s\+$/

set printheader=%<%f%h%m%=Page\ %N\ of\ %{(line('$')-1)/73+1}
