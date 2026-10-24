; Optional MAXTEXT startup client, independently written for VC.
; Copyright 2026 Mario Fetka. SPDX-License-Identifier: BSD-2-Clause
;
; Public DOS protocol: Open386MAX docs/maxtext.md, ABI 1.1.
; Called only from VC.COM's initial startup, before loading the overlay.
; No MAXTEXT code, headers or resident driver are linked into VC.
;
; The COM PSP already owns a DOS allocation. Its startup stack is bounded
; to the first 64 KiB by Init01. Borrow the NEXT 104 KiB only after checking
; the MCB owner/size and the conventional-memory boundary. Later startup
; reuses that area. No extra allocation, resize or resident memory is needed.

MxtScratchParas EQU 1A00h
MxtScratchStart EQU 1000h
MxtStartupParas EQU MxtScratchStart + MxtScratchParas

MxtDevice       DB 'MAXTEXT$',0
MxtStatus       DB 24 DUP(0)
MxtControl      DB 'MXTC'
                DW 1, 80
MxtTarget       DW 0
MxtScratch      DW 0
                DW MxtScratchParas
MxtResult       DW 0FFFFh

MaxTextStartup  PROC NEAR
                PUSHF
                PUSH AX
                PUSH BX
                PUSH CX
                PUSH DX
                PUSH SI
                PUSH DI
                PUSH BP
                PUSH DS
                PUSH ES
                PUSH CS
                POP DS
                MOV DX,OFFSET MxtDevice
                MOV AX,3D02h
                INT 21h
                JC @@Exit
                MOV BP,AX                 ; Handle, including valid handle zero
                MOV BX,BP
                MOV AX,4400h
                INT 21h
                JC @@Close
                TEST DL,80h               ; Ordinary MAXTEXT$ files are not devices
                JZ @@Close
                CALL MxtQuery
                JC @@Close
                CMP BYTE PTR MxtStatus[10],3
                JNE @@Close               ; Preserve graphics/mono/other modes
                CMP BYTE PTR MxtStatus[11],0
                JNE @@Close
                CMP WORD PTR MxtStatus[12],80
                JNE @@Close
                MOV AX,WORD PTR MxtStatus[22]
                MOV CX,50
                TEST AL,4
                JNZ @@Target
                MOV CL,43
                TEST AL,2
                JNZ @@Target
                MOV CL,25
                TEST AL,1
                JZ @@Close                ; Ignore unknown capability bits
  @@Target:     CMP WORD PTR MxtStatus[14],CX
                JE @@Close                ; Avoid clearing an already suitable screen
                MOV MxtTarget,CX
                MOV AX,CS
                DEC AX
                MOV ES,AX
                MOV AX,CS
                CMP ES:[1],AX             ; Only borrow our own PSP allocation
                JNE @@Close
                CMP WORD PTR ES:[3],MxtStartupParas
                JB @@Close
                ADD AX,MxtStartupParas
                JC @@Close
                CMP AX,0A000h
                JA @@Close
                SUB AX,MxtScratchParas
                MOV MxtScratch,AX
                MOV MxtResult,0FFFFh
                MOV DX,OFFSET MxtControl
                MOV CX,16
                MOV BX,BP
                MOV AX,4403h
                INT 21h
                JC @@Close                ; Never bypass a driver's rejection with BIOS
                CMP AX,16
                JNE @@Close
                CMP MxtResult,0
                JNE @@Close
                CALL MxtQuery             ; Validate the response after a successful set
                JC @@Close
                CMP WORD PTR MxtStatus[12],80
                JNE @@Close
                MOV AX,MxtTarget
                CMP WORD PTR MxtStatus[14],AX
                ; Normal VC initialization independently reads the actual BIOS
                ; geometry. A bad response must not trigger another mode set.
  @@Close:      MOV BX,BP
                MOV AH,3Eh
                INT 21h
  @@Exit:       POP ES
                POP DS
                POP BP
                POP DI
                POP SI
                POP DX
                POP CX
                POP BX
                POP AX
                POPF
                RET
MaxTextStartup  ENDP

MxtQuery        PROC NEAR
                MOV BX,BP
                MOV DX,OFFSET MxtStatus
                MOV CX,24
                MOV AX,4402h
                INT 21h
                JC @@Bad
                CMP AX,24
                JNE @@Bad
                CMP WORD PTR MxtStatus[0],584Dh ; 'MX'
                JNE @@Bad
                CMP WORD PTR MxtStatus[2],3154h ; 'T1'
                JNE @@Bad
                CMP BYTE PTR MxtStatus[5],1     ; Known ABI major
                JNE @@Bad
                CMP BYTE PTR MxtStatus[4],1     ; Control requires minor >= 1
                JB @@Bad
                CMP WORD PTR MxtStatus[6],24
                JNE @@Bad
                CLC
                RET
  @@Bad:        STC
                RET
MxtQuery        ENDP
