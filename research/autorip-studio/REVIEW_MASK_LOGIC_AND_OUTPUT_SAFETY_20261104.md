# AutoRIP Studio — revisão lógica de máscaras v0.72 (2026-11-04, 23h57 BRT)

**Escopo:** análise matemática do código e das evidências já registradas, somente leitura. Esta revisão **não** afirma ter reexecutado PRT/ICC, suíte Python ou verificado novos SHA-256 de arquivos originais nesta rodada. Não contém dados proprietários.

## Consequência demonstrável da coincidência das máscaras

Para cada posição de byte, sejam `a`, `b`, `c` os valores dos PRTs rotulados 0%, 50%, 100%. Defina `M_ab = (a != b)`, `M_ac = (a != c)`, `M_bc = (b != c)`.

Se **M_ab == M_ac** em uma região (como relatado para os planos candidatos 1 a 10), então:

- Se ambos forem falsos, `a=b=c`, portanto `M_bc` também é falso.
- Se ambos forem verdadeiros, `b` e `c` são diferentes de `a`, mas **podem ser iguais entre si ou diferentes**.
- Logo, **`M_bc` é subconjunto de `M_ab` e de `M_ac` nessa região**, mesmo que `M_bc` não apresente periodicidade de três planos.
- Isso explica por que periodicidade de `M_ab` e `M_ac` **não implica** periodicidade de `M_bc`. Não identifica intensidade, canal branco, quantização, perfil ICC ou semântica de pixels.

A relação é **local à região em que as máscaras foram demonstradas iguais**; não deve ser extrapolada para os planos candidatos 0 e 11.

## Testes sintéticos recomendados antes de qualquer alteração de código

1. `a=0,b=1,c=2`: `M_ab=M_ac=1`, `M_bc=1`.
2. `a=0,b=1,c=1`: `M_ab=M_ac=1`, `M_bc=0`.
3. `a=b=c=0`: todas as máscaras são 0.
4. Para buffers inteiros: `(a!=b)==(a!=c)` deve implicar `(b!=c) <= (a!=b)` elemento a elemento.
5. Em regiões de borda onde a igualdade não vale, **não** aplicar a inferência de subconjunto.
6. Repetir a leitura com blocos de tamanhos diferentes e comparar os hashes das máscaras para excluir dependência de particionamento.

## Revisão de segurança e limitações do código existente

- O `mask_periodicity.py` calcula SHA-256 das máscaras, **não** SHA-256 de valores raster por plano; máscaras iguais só significam posições alteradas iguais.
- Os limites de tamanho e a leitura em blocos reduzem consumo de memória, mas verificações de `stat` antes/depois **não são um snapshot atômico**. Não prometer resistência a adulteração concorrente.
- `Path.resolve()` protege contra apontar `--output` diretamente para o mesmo caminho resolvido de entrada, **mas não detecta aliases por hardlink**. O código de CLI atual usa `output.write_text()`; se o destino for um hardlink de um PRT de entrada, pode truncar/modificar o original. **Até corrigir, não executar CLI com destinos preexistentes e não confiáveis.** A função `inspect_periodicity` em si permanece somente leitura.
- Para correção futura: rejeitar destino existente (inclusive hardlinks), criar saída com `O_CREAT|O_EXCL` e política de não sobrescrita; preferir diretório dedicado, sem symlinks. Testar isso com fixtures sintéticas, antes de integrar.
- `layout_concentration.py` tem risco equivalente no destino `--output`.
- Nenhum resultado permite equiparar `Spot_1` a canal físico de branco, nem assumir DeviceN, CMYKW ou 2 bits por pixel.

## Estado

Revisão documental; sem novo teste executado neste ciclo. Nenhuma alteração de código não testada foi integrada. Não modificar `main`, não executar software proprietário, não gerar PRT de produção.
