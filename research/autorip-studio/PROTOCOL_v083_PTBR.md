# AutoRIP Studio — protocolo de coleta controlada v0.83 (somente pesquisa)

**Objetivo:** testar se o padrão de periodicidade identificado nos três arquivos TESTER1 se repete em novos arquivos, gerados a partir de **artes independentes**. A coleta não envolve envio à impressora, testes de cabeçote ou instalação de drivers.

**Softwares:** o RIP é o **FlexiPRINT MiniTX F-PRINT Edition**; o **PrintExp/Hoson** é o controlador da impressora, não o RIP.

## 1. Planejamento dos 12 arquivos

Use três arquivos de arte distintos e salve a mesma versão de cada um durante todas as exportações:

- `art_a`: composição de preenchimentos sólidos e bordas nítidas;
- `art_b`: linhas finas, texto e áreas vazias;
- `art_c`: gradientes, pequenos detalhes e transparência.

Crie cada arte com dimensões, perfil e resolução registrados. Para **cada** arte, gere PRTs com valores de branco **declarados pelo operador** em 0%, 50% e 100%. Refaça também a exportação em 50% uma segunda vez, sem copiar o PRT anterior. São **3 × (3 + 1) = 12 arquivos PRT**. O segundo PRT em 50% permite medir a repetibilidade binária da exportação.

Use os nomes propostos pelo gerador do manifesto, que inclui todos os casos: por exemplo, `art_a_white_0_r1.PRT`, `art_a_white_50_r1.PRT`, `art_a_white_50_r2.PRT` e `art_a_white_100_r1.PRT`.

## 2. Controle das variáveis

Mantenha constantes dentro de cada arte a imagem original, o tamanho físico, DPI, perfil ICC, modo de cor, qualidade/resolução de ripagem, número de passadas, configurações de saída e versão/preset do FlexiPRINT. **Somente** a configuração de branco deve variar nos três níveis. Registre esses parâmetros em um arquivo local `config_comum.txt`, sem senhas ou números de licença.

A identificação de cada arte vem do SHA-256 do arquivo de imagem **original**. O campo `common_config_sha256` é o SHA-256 do registro das configurações mantidas constantes. Esses campos são alegações documentais do operador; o verificador **não tem como comprovar** que as configurações do RIP foram efetivamente aplicadas.

Se o FlexiPRINT alterar internamente outro parâmetro quando o branco muda, registre a circunstância e **não interprete** a comparação como efeito isolado da porcentagem de branco.

## 3. Windows — gerar plano e coletar fingerprints

Abra o PowerShell a partir de `research/autorip-studio`:

~~~powershell
py -3.11 controlled_capture.py template --experiment-id pilot_001 --output "C:\AutoRIP-Piloto\plano.json"

(Get-FileHash "C:\AutoRIP-Piloto\config_comum.txt" -Algorithm SHA256).Hash.ToLowerInvariant()
(Get-FileHash "C:\AutoRIP-Piloto\art_a.png" -Algorithm SHA256).Hash.ToLowerInvariant()
(Get-FileHash "C:\AutoRIP-Piloto\amostras\art_a_white_0_r1.PRT" -Algorithm SHA256).Hash.ToLowerInvariant()
(Get-Item "C:\AutoRIP-Piloto\amostras\art_a_white_0_r1.PRT").Length
~~~

Adapte para os outros dois arquivos de arte e os outros onze arquivos PRT. Copie cada hash e tamanho para os campos correspondentes do plano. Todos os digests devem ter **64 caracteres hexadecimais minúsculos**. O plano criado por `template` contém campos em branco e **não constitui prova de integridade**.

Crie as pastas locais antes de executar os comandos e mantenha os PRTs fora do repositório GitHub.

## 4. Verificação final

~~~powershell
py -3.11 controlled_capture.py verify --manifest "C:\AutoRIP-Piloto\plano.json" --directory "C:\AutoRIP-Piloto\amostras" --output "C:\AutoRIP-Piloto\relatorio-verificado.json"
~~~

A operação é somente leitura para os 12 PRTs. O JSON derivado é criado apenas se todos os tamanhos e SHA-256 coincidirem com o manifesto previamente preenchido. **Um relatório existente nunca é substituído.**

O resultado registra a repetibilidade do nível 50% e possíveis igualdades binárias entre níveis diferentes, sem concluir que essas condições imprimiriam a mesma quantidade de tinta.

## 5. Critérios antes de estudar o layout

1. **Integridade:** todos os 12 arquivos verificados contra seus valores SHA-256 externos; nenhum arquivo reaproveitado por hardlink.
2. **Confundidores:** origem das artes diferente e demais parâmetros declaradamente congelados, salvo o nível de branco.
3. **Repetibilidade:** examinar se os rerips em 50% da mesma arte resultam em bytes iguais; se não, investigar metadados, variabilidade ou outros estados ocultos **antes** de atribuir alterações ao branco.
4. **Replicação:** só depois de passar pelos pontos anteriores, testar o período candidato de 17.472 bytes **sem ajustá-lo** aos novos dados; reportar acertos e falhas, inclusive se a geometria mudar.
5. **Interpretação:** nenhum resultado, isoladamente, comprova 2 bits, separação Spot_1, mapeamento CMYKW, perfis ICC ou compatibilidade com a controladora Hoson.

## 6. Segurança e limites

Não publicar PRTs, ICCs ou outros arquivos proprietários no GitHub. Não editar os PRTs originais. Não executar comandos na impressora. Não reproduzir chaves/licenças, caminhos privados ou identificação da máquina em relatórios públicos. `controlled_capture.py` valida os digests fornecidos: **não certifica a origem dos valores registrados, a execução do RIP nem a independência experimental das imagens.**

Os 12 arquivos são **necessários para o experimento futuro** e ainda não foram fornecidos. A suíte de testes usa exclusivamente dados sintéticos.
