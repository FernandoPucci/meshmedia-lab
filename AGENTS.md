# Instrucoes para agentes de codigo

Antes de implementar qualquer atividade no MeshMedia Lab:

1. Leia README.md, sdd/sdd.md, docs/implementation-status.md e docs/architecture.md.
2. Leia docs/OPENCODE-WORK-ORDER.md. Ele registra as decisoes recentes e a ordem de trabalho acordada.
3. Preserve a abordagem Specification-Driven Development (SDD): atualize primeiro a especificacao afetada, implemente em incrementos pequenos e mantenha testes, matriz de implementacao e changelog coerentes.
4. Nao trate capacidades propostas ou planejadas como implementadas.
5. Nao altere silenciosamente o formato binario MM1 v1 nem o significado de seus campos. Qualquer mudanca incompativel exige proposta explicita de nova versao ou extensao e testes de compatibilidade.
6. Nao faca refatoracoes amplas sem necessidade demonstrada. Preserve APIs e modulos existentes sempre que possivel.
7. Nao implemente itens marcados como FUTURO nesta ordem de trabalho.
8. Ao concluir cada etapa, informe arquivos alterados, decisoes tomadas, testes executados, resultados e pendencias. Nao declare testes aprovados sem executa-los.

O trabalho deve ser incremental e revisavel. Em caso de ambiguidade que altere o wire format, a compatibilidade ou o comportamento de transporte, documente alternativas e solicite decisao antes de codificar.
