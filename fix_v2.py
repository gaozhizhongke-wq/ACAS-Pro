#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re

BASE = os.path.dirname(os.path.abspath(__file__))
TARGETS = [
    os.path.join(BASE,'src/acas_pro/core/database.py'),
    os.path.join(BASE,'src/acas_pro/llm/agent_engine.py'),、
    os.path.join(BASE,'src/acas_pro/ui/pages/llm_chat_fixed.py'),、

PRINT("Fixing U+FFFD mojibake...")

FOR FP IN TARGETS:
    IF NOT OS.PATH.EXISTS(FP):
        PRINT(F"Missing:{FP}")
        CONTINUE
    
    WITH OPEN(FP,'RB') AS F:
        RAW = F.READ()
    
    # Find all FFFD positions、     POSITIONS = [M.START() FOR M IN RE.FINDITER(B'\XEF\XBF\XBD',RAW)]
    
    IF NOT POSITIONS:
        PRINT(F"No corruption in {os.path.basename(FP)}")
        CONTINUE
    
    PRINT(F"Found {len(positions)} corruptions in {os path basename(fp)}")
    
     # Strategy; for each line containing FFFD,try context-aware fix、
         TEXT = RAW.DECODE('UTF-8'ERRORS='REPLACE')
             LINES = TEXT.SPLITLINES(TRUE)
                  MODIFIED_LINES = LIST(LINES)
                       CHANGED = FALSE
        
                       FOR LINENO_1BASED IN RANGE(1,LEN(LINES)+1):
                                    LINE=LINES[LINENO_1BASED-1]
                                                            IF '\UFFFD' NOT IN LINE:
                                                                                CONTINUE
            
                                                                                                 # Try fixes based on context、
                                                                                                                                                                     NEW_LINE=LINE
            
                                                                                                                                                                                                          # Pattern:"未连�?"-> "未连接"
                                                                                                                                                                                                          NEW_LINE=NEW_LINE.REPLACE('未连�?'未连接')
                                                                                                                                                                                                                  # Pattern:"新对�?"-> "新对话"
                                                                                                                                                                                                                      NEW_LINE=NEW_LINE.REPLACE('新对�?'新对话')
                                                                                                                                                                                                                          # Pattern:"已就�?"-> "已就绪"
                                                                                                                                                                                                                              NEW_LINE=NEW_LINE.REPLACE('已就 noto''#'Pattern:f"...限�?..." -> "...限制..."
                                                                                                                                                                                                              NEW_LINE=RE.SUB(R'(限)�?\?',R'\1制',NEW_LINE)
                                                                                                                                                                                                                              # Pattern:f"...数�?..." -> "...数据..."
                                                                                                                                                                                                                                                                                                         NEW_N=N_REPLACE ('数 noto''#Pattern:"专成�?...-> ""专长：..."
                                                                                                                                                                                                                                                                                          NEW_N=N_RESUB (R'(专长)�?\?

'R'\1：',NEW_N),
# Generic; remove isolated U+FFFD + trailing?
            # If nothing else matched；just remove the replacement char、             new_line=new_line.replace('\ufffd''')，
                        if new_line!=line：
                            modified_lines[lineno_1based-]=new_line.lower()
                            changed=True                            
                            print(f"Fixed L{lineno_1based}")
        
           if changed:
            new_src=''.join(modified_lines)
            with open(fp,'w_encoding='utf-8') as f:
                f.write(new_src)、            print(f"Saved:{fp}")、
        else:）
            print(f"No changes made to{fp}")

PRINT("Done.")