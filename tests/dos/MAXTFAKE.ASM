; Deliberately incomplete MAXTEXT device for native VC failure-path tests.
; Copyright 2026 Mario Fetka. SPDX-License-Identifier: BSD-2-Clause
; Never changes video mode. Records control requests, then rejects them.
IFNDEF MXT_VERSION
MXT_VERSION EQU 0101h
ENDIF
IFNDEF MXT_MODES
MXT_MODES EQU 7
ENDIF
IFNDEF MXT_COUNT
MXT_COUNT EQU 24
ENDIF
IFNDEF MXT_SIZE
MXT_SIZE EQU 24
ENDIF
IFNDEF MXT_BADSIG
MXT_BADSIG EQU 0
ENDIF
TEXT SEGMENT
ASSUME CS:TEXT, DS:TEXT
ORG 0
        DD -1
        DW 0C800h
        DW Strategy, Interrupt
        DB 'MAXTEXT$'
Request DD 0
        DB 'VCMXTFIX'
Status  DB 'MXT1'
        DW MXT_VERSION, MXT_SIZE, 1
        DB 3,0
        DW 80,25,16
LastRow DW 0
SetCount    DW 0
        DW MXT_MODES

Strategy PROC FAR
        MOV WORD PTR CS:Request,BX
        MOV WORD PTR CS:Request+2,ES
        RET
Strategy ENDP

Interrupt PROC FAR
        PUSH AX
        PUSH BX
        PUSH CX
        PUSH DX
        PUSH SI
        PUSH DI
        PUSH DS
        PUSH ES
        PUSH CS
        POP DS
        LES BX,Request
        MOV AX,8103h
        CMP BYTE PTR ES:[BX+2],0
        JE Init
        CMP BYTE PTR ES:[BX+2],13
        JE Done
        CMP BYTE PTR ES:[BX+2],14
        JE Done
        CMP BYTE PTR ES:[BX+2],3
        JE Input
        CMP BYTE PTR ES:[BX+2],12
        JNE Finish
        LES DI,ES:[BX+14]
        MOV AX,ES:[DI+8]
        MOV LastRow,AX
        INC SetCount
        MOV WORD PTR ES:[DI+14],3
        LES BX,Request
        MOV WORD PTR ES:[BX+18],0
        MOV AX,810Ch
        JMP Finish
Input:  MOV WORD PTR ES:[BX+18],MXT_COUNT
        LES DI,ES:[BX+14]
        MOV SI,OFFSET Status
        MOV CX,MXT_COUNT
        CLD
        REP MOVSB
        JMP Done
Init:   MOV WORD PTR ES:[BX+14],OFFSET DriverEnd
        MOV ES:[BX+16],CS
        IF MXT_BADSIG
        MOV BYTE PTR Status,'B'
        ENDIF
Done:   MOV AX,0100h
Finish: LES BX,Request
        MOV ES:[BX+3],AX
        POP ES
        POP DS
        POP DI
        POP SI
        POP DX
        POP CX
        POP BX
        POP AX
        RET
Interrupt ENDP
DriverEnd LABEL BYTE
TEXT ENDS
END
