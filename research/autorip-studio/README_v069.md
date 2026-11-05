# AutoRIP Studio v0.69 — laboratório somente leitura

Este código é experimental e independente do FluxoRIP. Não pode gerar PRT de produção nem controlar impressoras.

**Pré-requisitos:** Python 3.11+ (testado em Python 3.13.5). Sem dependências de terceiros.

**Testes:** no diretório destes arquivos, rode `python -m unittest discover -p 'test_*.py' -v`.

**Leitura PRT:** `python layout_hypotheses.py caminho.prt` (assina/valida `0x5555`, compara `48 + rows × slots × stride`, calcula SHA-256). `python prt_diff.py a.prt b.prt` compara duas hipóteses de layout. `python prt_white_experiment.py --white-0 a.prt --white-50 b.prt --white-100 c.prt` compara três porcentagens de branco **declaradas**, nunca inferidas. A geometria da experiência exige 12 faixas; sua posição física é desconhecida.

**Leitura ICC:** `python icc_inspect.py perfil.icc` e `python icc_manifest.py pasta`. O inventário exclui symlinks sem segui-los.

**DeviceN:** `python devicen_inspect.py config.txt` extrai nomes lógicos de um texto por parsing estático. **Não executa** o conteúdo.

**Segurança:** nunca use arquivos de produção em diretórios modificáveis por terceiros sem cópia isolada e autorizada; não publique bytes proprietários, não execute softwares proprietários, não controle hardware e não altere licenças. Os testes fazem apenas pequenas amostras sintéticas `.bin` temporárias. Não há comprovação de mapeamento CMYKW.
