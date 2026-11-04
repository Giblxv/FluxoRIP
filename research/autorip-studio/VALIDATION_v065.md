# AutoRIP Studio v0.65 — validação experimental (04/11/2026)

O código local `prt_diff.py` foi refatorado para comparar simultaneamente hipóteses row-major e plane-major em uma única passagem sequencial pelo payload, com verificação de SHA-256 contra a inspeção inicial e offsets de diferenças no cabeçalho.

**Execução local comprovada:** `python -m unittest discover -p 'test_*.py' -v` → 36 testes, 0 falhas (33 anteriores + 3 novos). Testes com arquivos sintéticos, sem PRT real ou hardware. SHA-256 do patch local: `1ab280c69e9efb3b7e997fc1651646d47134831f4a41e624000d0ddb1e5cddb8`. SHA-256 do módulo: `572d36298d4c5c7272eb827276a41bf2944eb4b823a785aaabab42feb61ba8f1`.

**Drive acessível:** 168 itens no nível superior da pasta compartilhada, incluindo `Jobs and Settings`, `ICCProfile`, `Profiles`, `Samples`, `Spot Colors` e `VSDProfile`. Nenhum PRT real foi baixado ou analisado nesta rodada.

**Proveniência e limites:** este documento registra um patch **gerado localmente, ainda não importado para esta branch**. Não afirmar que a branch contém o código v0.65 antes do upload dos fontes. Não há evidência para mapear as 12 faixas em canais CMYKW. Não executar binários proprietários, publicar perfis comerciais ou controlar impressoras.

**Próximas etapas:** importar fontes e testes validados, localizar amostras 0/50/100, verificar hashes e discriminar hipóteses de layout por evidência espacial.
