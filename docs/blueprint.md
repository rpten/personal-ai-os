<!-- Fonte: La_Fabrica_Blueprint_v1.docx (Rafael, 06/11/2026). Arquitetura-alvo; o estado real está em docs/auditoria.md. -->

**LA FÁBRICA**

**Blueprint v1 --- Arquitetura e operação**

# 1. Propósito

La Fábrica é um ecossistema pessoal de desenvolvimento assistido por IA.
Transforma ideias em aplicações entregues, mantendo contexto, decisões,
execução e resultados centralizados. O usuário atua como diretor/Product
Owner; os agentes assumem o trabalho operacional e técnico.

# 2. Princípios

-   Direção humana; execução autônoma durante tarefas acionadas.

-   Uma fonte de verdade para contexto, decisões, estado e entregas.

-   Conversa e dashboard são interfaces complementares.

-   QA, diagnóstico e correção automatizados sempre que possível.

-   Interromper o usuário somente por decisão, autorização ou
    impedimento real.

-   Toda execução termina em entrega verificável, bloqueio explicado ou
    pedido objetivo.

-   A Construtora é um componente; aplicações são produtos separados.

# 3. Organograma conceitual

## LA FÁBRICA --- Ecossistema

-   Jarvis --- interface conversacional: captura, descoberta, feedback,
    decisões e acionamento.

-   Command Center --- painel visual: status, marcos, bloqueios,
    entregas e ações pendentes.

-   Context & Memory --- contexto pessoal, preferências, histórico e
    conhecimento reutilizável.

-   Construtora --- desenvolvimento de aplicações, execução de agentes,
    QA, correções e entrega.

-   Applications --- produtos independentes (ex.: Personal Assistant /
    Second Brain).

-   Shared Foundation --- documentação, estado, eventos, permissões e
    integrações.

# 4. Componentes e responsabilidades

## Jarvis

Receber ideias e comandos; conduzir descoberta com uma pergunta por vez;
consolidar brief; solicitar aprovação de plano; acompanhar e entregar
resultados. Não exige operação técnica do usuário.

## Command Center

Visão consolidada por projeto: etapa, status, último evento, próximo
marco, bloqueio, decisão pendente, entregáveis e histórico.

## Context & Memory

Contexto durável: preferências, decisões, requisitos e aprendizados.
Distinguir fatos, hipóteses e decisões revogadas.

## Construtora

Receber tarefa autorizada; planejar; decompor em marcos; executar
agentes; integrar código; testar; corrigir; produzir evidências;
atualizar estado e entregar.

## Applications

Cada app tem escopo, documentação, código, ambiente, testes, releases e
estado próprios.

## Shared Foundation

IDs estáveis, esquema de estado, eventos, documentação canônica,
permissões, GitHub e notificações.

# 5. Fluxo ponta a ponta

1.  **Captura ---** Usuário registra ideia em Jarvis.

2.  **Descoberta ---** Jarvis esclarece objetivo, público, problema,
    restrições e sucesso --- uma pergunta por vez.

3.  **Brief ---** Consolidação em escopo, hipóteses, requisitos e
    critérios de aceite.

4.  **Planejamento ---** Construtora propõe arquitetura, etapas,
    dependências, riscos e entregáveis.

5.  **Aprovação ---** Usuário aprova decisões de produto, não detalhes
    técnicos rotineiros.

6.  **Execução ---** Agentes trabalham por etapa e registram progresso e
    artefatos.

7.  **QA e correção ---** Testes automatizados; falhas acionam correção
    e nova validação.

8.  **Entrega ---** Aplicação/artefato, evidências, limitações e
    instruções de uso.

9.  **Encerramento ---** Estado e documentação atualizados; execução
    para até novo acionamento.

# 6. Modelo mínimo de estado por projeto

-   project_id, nome, objetivo e owner.

-   Status e fase: discovery, brief, plan, execution, QA, delivery ou
    blocked.

-   Brief aprovado, requisitos e critérios de aceite.

-   Marcos, agentes/responsáveis, status, dependências e evidências.

-   Último evento, timestamp e próxima ação.

-   Bloqueios, decisões pendentes e responsável.

-   Links de repositório, PRs, releases e entregáveis.

-   Registro de decisões e mudanças de escopo.

# 7. Acionamento e confiabilidade

-   Ideia registrada pelo fluxo normal inicia descoberta sem label
    manual escondida.

-   Evento ignorado gera explicação visível; workflow verde não pode
    significar falsamente trabalho realizado.

-   Estados distintos: recebido, aceito, execução, concluído, bloqueado,
    falhou e ignorado.

-   Idempotência e proteção contra execução duplicada.

-   Testes automáticos de gatilhos, guardas e transições.

-   Infraestrutura da Construtora com regressão e rollback.

-   Ações pagas, irreversíveis ou sensíveis exigem autorização.

-   Execução sob demanda; agentes param ao concluir ou bloquear.

# 8. QA e evidências

Validação automatizada proporcional ao produto:

-   Resultados dos testes e cobertura pertinente.

-   Build/deploy e URL ou artefato final.

-   Checagens de console, erros e regressões quando aplicáveis.

-   Capturas ou vídeo de fluxos críticos quando úteis.

-   Critérios verificados e não verificados.

-   Limitações e risco residual, sem declarar sucesso indevido.

O usuário não executa QA técnico. Se a validação exigir julgamento de
produto, o sistema faz uma pergunta objetiva.

## 8.1 Design Capability (adicionado em 07/11/2026)

Design é uma capacidade da Construtora, não uma instrução que depende de ser
lembrada. Todo marco que cria ou altera interface segue um workflow
obrigatório: brief → direção visual → UX → implementação → QA visual com
prints reais → inspeção e correção → revalidação → entrega com evidência.

-   QA visual e QA funcional são distintos: build e testes verdes não tornam
    um frontend pronto.

-   Direção visual (identidade por produto) e regras de UX/acessibilidade vêm
    de Skills auditadas e versionadas no repositório; a infraestrutura
    (base técnica, QA, modelos) é compartilhada, a identidade não.

-   O verificador confere os artefatos de design e roda o QA visual de novo,
    de forma independente do agente.

Detalhes: `docs/design.md`.

# 9. Command Center --- conteúdo mínimo

-   Visão geral: projetos ativos, fila, concluídos e bloqueados.

-   Cartão por projeto: objetivo, fase, marcos, último evento e próxima
    ação.

-   Área "Preciso de você": decisões e aprovações estritamente
    necessárias.

-   Entregas: links, releases, arquivos e evidências.

-   Histórico em linguagem humana, incluindo falhas.

-   Ações rápidas: nova ideia, retomar, aprovar plano e abrir entrega.

# 10. Roadmap

## P0 --- Confiabilidade e fonte de verdade

Corrigir gatilho natural; estados explícitos; feedback de execução;
testes de trigger/guard; documentação canônica.

## P1 --- Ciclo de projeto

Discovery → brief → plano → aprovação → execução → QA → entrega; estado
persistente e marcos.

## P2 --- Command Center

Dashboard conectado à fonte de verdade, com projetos, bloqueios,
decisões e entregas.

## P3 --- Jarvis integrado

Captura e acompanhamento conversacional conectados ao estado, sem
duplicar contexto.

## P4 --- Context & Memory

Memória compartilhada com origem, validade, atualização e recuperação
por projeto.

## P5 --- Aplicações

Construir apps individuais (começando pelo Personal Assistant/Second
Brain) sobre a Construtora confiável.

# 11. Critérios de sucesso

-   Ideia registrada normalmente é reconhecida e recebe resposta
    visível.

-   Usuário vê estado e próxima ação sem abrir logs ou investigar
    GitHub.

-   Sistema distingue execução, skip, falha, bloqueio e conclusão.

-   Agentes atualizam documentação/estado sem copiar e colar manual.

-   QA e correção são conduzidos pelos agentes; evidências acompanham a
    entrega.

-   Usuário é interrompido apenas por decisão ou autorização relevante.

-   Cada app tem escopo e ciclo próprios, separados da Construtora.

# 12. Limites e decisões em aberto

Este Blueprint é arquitetura-alvo v1, não afirma que tudo já existe. A
auditoria deve classificar requisitos como implementados, parciais,
ausentes ou contraditórios, com evidências. Serviços pagos, permissões e
ações irreversíveis dependem de autorização.

# Apêndice --- Prompt para Claude

Trabalhe no repositório rpten/personal-ai-os usando este Blueprint como
especificação.\
\
1. Audite o repositório e compare cada seção com a implementação real.
Classifique: implementado, parcial, ausente ou contraditório; cite
arquivos e evidências.\
2. Identifique inconsistências em gatilhos, estados, documentação,
feedback, QA e experiência do usuário.\
3. Proponha plano priorizado por dependências. Não comece o Personal
Assistant/Second Brain.\
4. Implemente primeiro P0 (confiabilidade e fonte de verdade), com
regressão automatizada. Ideias pelo fluxo natural não podem exigir
labels manuais.\
5. Dê feedback explícito para execução, skip, falha, bloqueio e
conclusão. Workflow verde não equivale a tarefa concluída.\
6. Atualize documentação e estado canônicos; evite fontes concorrentes e
contexto duplicado.\
7. Faça QA automatizado, corrija falhas e registre evidências. Não peça
ao usuário para inspecionar logs, screenshots, testes ou fazer
troubleshooting.\
8. Não altere serviços pagos, permissões, ações irreversíveis ou
arquitetura externa sem autorização explícita.\
9. Organize mudanças em commits/PRs claros, respeitando proteções. Se
não puder agir, declare o bloqueio; não alegue execução.\
10. Reporte: concluído; evidências; pendências/bloqueios; decisão
necessária; próxima ação concreta.\
\
Você é responsável pela execução técnica ponta a ponta. O usuário é
diretor/Product Owner, não operador de QA.
