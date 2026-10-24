;---------------------------------------------------------------
;		Help (F1)
;
;	VC.HLP is a Norton Guides file (as of VC 4.05): an index
;	(a short entry: one line per topic) and the topics (long
;	entries). HlpPage n shows the topic of line HelpMap[n] of
;	the index, 0 the index.
;
;		Version:	24.10.2026
;---------------------------------------------------------------

HlpData		STRUC
		DB	HelpBuf DUP(?)
  HlpHndl	DW	?		; Handle of VC.HLP
  HlpRoot	DD	?		; Offset of the index
  HlpTopic	DW	?		; Line of the index shown
  HlpIdxCur	DW	?		; Cursor in the index
  HlpIdxFirst	DW	?		; First line of the index shown
  HlpMode	DW	?		; Entry: 0 - short (index), 1 - long
  HlpSize	DW	?		; Size of entry
  HlpLins	DW	?		; Number of lines
		DW	?		; See also
		DW	?		; Parent line
		DD	?		; Parent offset
		DW	?, ?		; Parent menu, prompt
		DD	?		; Previous
		DD	?		; Next
  HlpInfo	DB	?		; Entry (short: 6 bytes per line, lines)
HlpData		ENDS

HlpHead		EQU	1Ah		; Size of entry header
ListSave	EQU	(SIZEOF ListData - ListCurFlag + 1) / 2

		.CONST
Help_F		DB	'VC.HLP',0
Help_S		DB	' Help ',0
HlpEr1_S	DB	'There was error reading data',0
HlpEr2_S	DB	'from the help file.',0
HlpMn1_S	DB	'[ Help ]',0FFh,3,'[ Cancel ]',0
HlpMn2_S	DB	'[ Next ]',0FFh,3,'[ Previous ]',0FFh,3,'[ Index ]',0FFh,3,'[ Cancel ]',0

		.DATA
; Generated from stable topic IDs; rebuild together with VC.HLP.
		INCLUDE ../build/help/VCHELPMAP.INC
HlpCurs_P	DB	HlpRe_C, HlpRe_C, HlpRe_C, HlpRe_C
HlpIdx_P	DB	Help_C, HlpRe_C, HlpBo_C, HlpUn_C
		DW	Help_S
		DW	0FFFFh
		DW	0FFFEh
		DW	0FFFFh
		DW	HlpMn1_S
		DW	0
HlpIdx_B	BOXHD	< HlpIdx_P, 8200h, HlpProc, Dialog_K, Def_M, 0, 0 >
		BOXMN	< 4, 0,0,0,0, 0FCF6h, HlpMn1_D,, 0 >
		DB	0
HlpTxt_P	DB	Help_C, HlpRe_C, HlpBo_C, HlpUn_C
		DW	Help_S
		DW	0FFFFh
		DW	0FFFEh
		DW	0FFFFh
		DW	HlpMn2_S
		DW	0
HlpTxt_B	BOXHD	< HlpTxt_P, 8200h, HlpProc, Dialog_K, Def_M, 0, 0 >
		BOXMN	< 4, 0,0,0,0, 0FCE8h, HlpMn2_D,, 0 >
		DB	0
HlpErr_P	DB	Err_C, ErInv_C, ErInv_C, 0
		DW	Help_S
		DW	HlpEr1_S
		DW	HlpEr2_S
		DW	Ok_S
		DW	0
HlpErr_B	BOXHD	< HlpErr_P, 900h, 0, Dialog_K, Def_M, 0, 0 >
		BOXMN	< 4, 0,0,0,0, 4FEh, OkMn_D,, 0 >
		DB	0
HlpMn1_D	DB	 8,  0
		DB	10, 11
		DB	 0
HlpMn2_D	DB	 8,  0
		DB	12, 11
		DB	 9, 26
		DB	10, 38
		DB	 0

;---------------------------------------------------------------
;	Help
;		ES - data segment
;---------------------------------------------------------------
		.CODE	Subs
Help		PROC	FAR USES AX BX CX DX SI DI BP DS

		PUSH	ES
		POP	DS
		MOV	AL,0FFh			; No help in help
		XCHG	AL,DS:HlpPage
		MOV	AH,1
		XCHG	AH,DS:BlocEr
		PUSH	AX
		CMP	AL,None_H
		JNE	@@Start
		JMP	@@Exit
  @@Start:	PUSH	AX
		MOV	AH,3			; Hide cursor
		MOV	BH,DS:ScrPage
		INT	10h
		POP	AX
		PUSH	CX
		CALL	HidCur
		MOV	SI,OFFSET ListCurFlag	; Save list of the dialog
		MOV	CX,ListSave
  @@SaveList:	PUSH	WORD PTR DS:[SI]
		INC	SI
		INC	SI
		LOOP	@@SaveList
		MOV	BL,AL
		MOV	BH,0
		MOV	AL,0
		CMP	BX,MaxHelp
		JAE	@@Page
		MOV	AL,CS:HelpMap[BX]
  @@Page:	PUSH	AX
		MOV	DS:HlpHndl,0
		MOV	SI,OFFSET Help_F	; Open VC.HLP
		MOV	DI,OFFSET HlpInfo
		MOV	DX,DI
		CALL	MainFil
		CALL	ChgDisk
		JC	@@Error1
		MOV	AL,40h
		CALL	OpenFil
		JC	@@Error1
		MOV	DS:HlpHndl,AX
		XOR	CX,CX			; Norton Guides
		XOR	DX,DX
		MOV	SI,2
		MOV	DI,OFFSET HlpInfo
		CALL	HlpRead
		JC	@@Error1
		CMP	WORD PTR DS:HlpInfo,'GN'
		JNE	@@Error1
		MOV	DX,194h			; Index
		MOV	SI,4
		MOV	DI,OFFSET HlpRoot
		CALL	HlpRead
		JC	@@Error1
		CALL	HlpDecode
		XOR	AX,AX
		MOV	DS:HlpIdxCur,AX
		MOV	DS:HlpIdxFirst,AX
		POP	AX
		MOV	AH,0
		DEC	AX
		MOV	DS:HlpTopic,AX
		JNS	@@Topic

  @@Index:	CALL	HlpRdIndex		; Index
		JC	@@Error
		MOV	AX,DS:HlpIdxCur
		MOV	DS:ListCursor,AX
		MOV	AX,DS:HlpIdxFirst
		MOV	DS:ListFirst,AX
		MOV	BP,OFFSET HlpIdx_B
		CALL	HlpDialog
		MOV	CX,DS:ListCursor
		MOV	DS:HlpIdxCur,CX
		MOV	CX,DS:ListFirst
		MOV	DS:HlpIdxFirst,CX
		JNE	@@Close
		MOV	CX,DS:HlpIdxCur
		MOV	DS:HlpTopic,CX

  @@Topic:	CALL	HlpRdIndex		; Topic
		JC	@@Error
		MOV	AX,DS:HlpTopic
		CMP	AX,DS:HlpLins
		JB	@@ReadTopic
		XOR	AX,AX			; After the last: the first
		CMP	DS:HlpTopic,0FFFFh
		JNE	@@SetTopic
		MOV	AX,DS:HlpLins		; Before the first: the last
		DEC	AX
  @@SetTopic:	MOV	DS:HlpTopic,AX
  @@ReadTopic:	MOV	SI,AX
		ADD	SI,SI
		ADD	SI,AX
		ADD	SI,SI
		MOV	DX,WORD PTR DS:HlpInfo[SI+2]
		MOV	CX,WORD PTR DS:HlpInfo[SI+4]
		CALL	HlpEntry
		JC	@@Error
		CMP	DS:HlpMode,1
		JNE	@@Error
		XOR	AX,AX
		MOV	DS:ListCursor,AX
		MOV	DS:ListFirst,AX
		MOV	BP,OFFSET HlpTxt_B
		CALL	HlpDialog
		CMP	AL,1
		JB	@@Next
		JE	@@Previous
		CMP	AL,2
		JE	@@Index
		JMP	@@Close
  @@Next:	INC	DS:HlpTopic		; Next
		JMP	@@Topic
  @@Previous:	DEC	DS:HlpTopic		; Previous
		JMP	@@Topic

  @@Error1:	POP	AX
  @@Error:	MOV	BP,OFFSET HlpErr_B	; Error
		CALL	Dialog
  @@Close:	MOV	BX,DS:HlpHndl		; Close
		OR	BX,BX
		JE	@@Restore
		MOV	AH,3Eh
		CALL	Intr21
  @@Restore:	MOV	SI,OFFSET ListCurFlag+2*(ListSave-1)
		MOV	CX,ListSave
  @@RestList:	POP	WORD PTR DS:[SI]
		DEC	SI
		DEC	SI
		LOOP	@@RestList
		POP	CX			; Restore cursor
		MOV	AH,1
		INT	10h
  @@Exit:	POP	AX
		MOV	DS:HlpPage,AL
		MOV	DS:BlocEr,AH
		RET
Help		ENDP

;---------------------------------------------------------------
;	Help dialog
;		CS:BP - dialog (BOXHD)
;	Return:	   AL - menu item, 0FFh - Esc
;		   ZF - first item
;---------------------------------------------------------------
HlpDialog	PROC	NEAR USES BX CX DX SI DI

		MOV	AL,DS:Columns		; Window: 64 columns at most
		SUB	AL,12
		CMP	AL,LenStr
		JBE	@@Width
		MOV	AL,LenStr
  @@Width:	MOV	AH,DS:Lines
		SUB	AH,11
		MOV	DS:ListWindow,AX
		MOV	DS:ListBase,305h
		MOV	AX,DS:HlpLins
		MOV	DS:ListTotal,AX
		MOV	DS:ListLine,OFFSET HlpItem
		MOV	DS:ListHotKey,0
		MOV	DX,OFFSET HelpMap
		CALL	Dialog
		RET
HlpDialog	ENDP

;---------------------------------------------------------------
;	Help dialog subfunction
;---------------------------------------------------------------
HlpProc		PROC	NEAR

		CMP	AX,0FFFFh
		JE	@@Init
		CMP	AH,0FCh
		JAE	@@DialList
		CMP	DS:HlpMode,0
		JE	@@DialList
		MOV	SI,DS:ListFirst		; Text: keys scroll it
		CMP	AX,4800h
		JE	@@SetCursor
		CMP	AX,4900h
		JE	@@SetCursor
		CMP	AX,5000h
		JE	@@Bottom
		CMP	AX,5100h
		JNE	@@DialList
  @@Bottom:	PUSH	CX
		MOV	CL,DS:ListWindow.Y
		MOV	CH,0
		ADD	SI,CX
		POP	CX
		DEC	SI
		CMP	SI,DS:ListTotal
		JB	@@SetCursor
		MOV	SI,DS:ListTotal
		DEC	SI
  @@SetCursor:	MOV	DS:ListCursor,SI
		JMP	@@DialList
  @@Init:	MOV	DS:MinMnuFlag,1
  @@DialList:	CALL	DialogList
		RET
HlpProc		ENDP

;---------------------------------------------------------------
;	Output help line
;		   SI - line
;		   DI - first line in window
;		BH,BL - base of dialog
;		CS:BP - colors (+1 - cursor)
;---------------------------------------------------------------
HlpItem		PROC	NEAR USES AX CX SI DI BP ES

		MOV	AX,SI
		SUB	AX,DI
		ADD	BX,DS:ListBase
		ADD	BH,AL
		MOV	AX,OFFSET HlpTxt_P	; Text: no cursor
		CMP	DS:HlpMode,0
		JNE	@@Colors
		MOV	AX,OFFSET HlpIdx_P
		CMP	BP,AX
		JE	@@Colors
		MOV	AX,OFFSET HlpCurs_P
  @@Colors:	MOV	BP,AX
		CALL	HlpLine
		MOV	DL,DS:ListWindow.X
		MOV	DH,1
		CALL	BasAdr
		MOV	AH,CS:[BP]
		CALL	Color
		MOV	AL,' '
		MOV	CL,DL
		MOV	CH,0
		REP	STOSW
		MOV	AL,DL
		CALL	NgLine
		CLC
		RET
HlpItem		ENDP

;---------------------------------------------------------------
;	Address of help line
;		   SI - line
;	Return:	   SI - address
;---------------------------------------------------------------
HlpLine		PROC	NEAR USES AX CX DX DI ES

		PUSH	DS
		POP	ES
		MOV	DI,OFFSET HlpInfo
		CMP	DS:HlpMode,0
		JNE	@@Find
		MOV	AX,6			; Index: offsets first
		MUL	DS:HlpLins
		ADD	DI,AX
  @@Find:	MOV	CX,SI
		MOV	AL,0
		JCXZ	@@Exit
  @@Next:	PUSH	CX
		MOV	CX,0FFFFh
		REPNE	SCASB
		POP	CX
		LOOP	@@Next
  @@Exit:	MOV	SI,DI
		RET
HlpLine		ENDP

;---------------------------------------------------------------
;	Read index
;---------------------------------------------------------------
HlpRdIndex	PROC	NEAR USES CX DX

		MOV	DX,DS:HlpRoot.Lo
		MOV	CX,DS:HlpRoot.Hi
		CALL	HlpEntry
		JC	@@Exit
		CMP	DS:HlpMode,0
		JE	@@Exit
		STC
  @@Exit:	RET
HlpRdIndex	ENDP

;---------------------------------------------------------------
;	Read entry
;		CX:DX - offset
;	Return:	   CY - error
;---------------------------------------------------------------
HlpEntry	PROC	NEAR USES SI DI

		MOV	SI,HlpHead
		MOV	DI,OFFSET HlpMode
		CALL	HlpRead
		JC	@@Exit
		CALL	HlpDecode
		MOV	SI,DS:HlpSize
		CMP	SI,HelpBuf+LenHelp-HlpInfo
		CMC
		JC	@@Exit
		ADD	DX,HlpHead
		ADC	CX,0
		MOV	DI,OFFSET HlpInfo
		CALL	HlpRead
		JC	@@Exit
		CALL	HlpDecode
  @@Exit:	RET
HlpEntry	ENDP

;---------------------------------------------------------------
;	Read from VC.HLP
;		CX:DX - offset
;		DS:DI - buffer
;		   SI - number of bytes
;	Return:	   CY - error
;---------------------------------------------------------------
HlpRead		PROC	NEAR USES AX BX CX DX

		MOV	BX,DS:HlpHndl
		MOV	AX,4200h
		CALL	Intr21
		JC	@@Exit
		MOV	DX,DI
		MOV	CX,SI
		MOV	AH,3Fh
		CALL	Intr21
		JC	@@Exit
		CMP	AX,CX
		JE	@@Exit
		STC
  @@Exit:	RET
HlpRead		ENDP

;---------------------------------------------------------------
;	Decode what HlpRead read
;		DS:DI - buffer
;		   SI - number of bytes
;---------------------------------------------------------------
HlpDecode	PROC	NEAR USES CX DI

		MOV	CX,SI
  @@Next:	XOR	BYTE PTR DS:[DI],1Ah
		INC	DI
		LOOP	@@Next
		RET
HlpDecode	ENDP
