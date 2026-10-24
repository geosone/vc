@ JWASM -q -c -DOFFICIAL %1.ASM
@ IF errorlevel==1 GOTO End
@ IF "%1"=="vcovl" GOTO Ovl
@ IF "%1"=="VCOVL" GOTO Ovl
@ JWLINK format dos com file %1.OBJ name %1.COM
@ IF errorlevel==1 GOTO End
@ DEL %1.OBJ
@ GOTO End
:Ovl
@ JWLINK format dos file %1.OBJ name VC.OVL
@ IF errorlevel==1 GOTO End
@ DEL %1.OBJ
:End
