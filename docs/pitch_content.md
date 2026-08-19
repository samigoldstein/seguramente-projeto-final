# Pitch Deck — D&O Policy Intelligence

## Direção visual

Use uma estética editorial de tecnologia aplicada a seguros: fundo azul-marinho, branco, azul-claro e acento âmbar. Priorize títulos curtos, tabelas compactas, cartões de métricas e diagramas limpos. O deck deve ser visualmente legível em apresentação oral e não substituir o relatório técnico.

## Slide 1 — Capa

**D&O Policy Intelligence**  
Análise e comparação explicável de apólices D&O

Projeto Final — InsurMinds  
MVP funcional | 19 de agosto de 2026

Visual: título forte, subtítulo curto e uma linha de fluxo documental PDF → IA → comparação.

## Slide 2 — O problema

Apólices D&O são extensas, jurídicas e difíceis de comparar manualmente.

O especialista precisa localizar limites, franquias, coberturas, exclusões e condições em documentos com estruturas diferentes.

**O custo oculto:** horas de leitura mecânica antes da análise de negócio.

Visual: documento longo à esquerda e uma tabela fragmentada à direita.

## Slide 3 — A proposta

O D&O Policy Intelligence transforma duas apólices em uma comparação rastreável.

**Receber → extrair → estruturar → armazenar → consultar → comparar → explicar.**

A solução não substitui o especialista. Ela reduz o trabalho de localização e preserva o trecho original para revisão.

## Slide 4 — MVP demonstrável

O usuário pode:

1. Fazer upload de dois PDFs ou imagens.
2. Extrair texto nativo ou aplicar OCR.
3. Estruturar 19 campos D&O.
4. Pesquisar por categoria ou campo.
5. Comparar Apólice A e Apólice B.
6. Abrir evidências por página.

Visual: jornada horizontal com seis etapas e um cartão de “revisão humana”.

## Slide 5 — Arquitetura

**Ingestor → PDF/OCR → texto por página → extração estruturada → validação → SQLite → consulta/comparação → interface.**

Agentes especializados mantêm responsabilidades separadas e tornam o fluxo explicável.

Visual: usar `docs/assets/architecture.png` como diagrama principal.

## Slide 6 — IA com controle

O modelo recebe texto e campos autorizados.

A saída precisa preservar:

- status do campo;
- valor;
- página;
- trecho de evidência;
- confiança.

Quando a resposta vem incompleta, o pipeline aplica fallback determinístico local. A comparação principal não depende de um resumo livre da IA.

Callout: **“Não localizado” não significa “excluído”.**

## Slide 7 — Comparação explicável

O schema alinha 19 campos em sete grupos:

**Identificação | Limites | Retenções | Coberturas | Extensões | Exclusões | Condições**

Estados possíveis: igual, diferente, ausente, ambíguo ou não aplicável.

Cada diferença mostra os valores de A e B, as páginas e os trechos de origem.

## Slide 8 — Resultado validado

**2** documentos processados  
**6** páginas extraídas  
**19** campos comparados  
**11** diferenças ou lacunas identificadas  
**6** testes automatizados aprovados

Exemplos: limite de R$ 10 milhões vs. R$ 15 milhões; franquia de R$ 50 mil vs. R$ 100 mil; período adicional de 24 vs. 36 meses.

Visual: quatro cartões de métricas e uma linha comparativa.

## Slide 9 — Limites e evolução

O corpus é sintético e autoral. O MVP não substitui parecer jurídico, subscrição ou decisão de cobertura.

Próximos passos:

- revisão humana dos fatos;
- múltiplas versões da mesma apólice;
- recuperação contextual por cláusula;
- exportação de relatório comparativo;
- corpus público com licenças verificadas.

## Slide 10 — Encerramento e entrega

**Uma camada de inteligência documental para transformar leitura em decisão revisável.**

O pacote inclui:

- MVP Streamlit;
- relatório técnico PDF;
- código e testes;
- evidências JSON;
- Pitch Deck;
- vídeo de demonstração;
- licença MIT e README.

Mensagem final: **IA para localizar, estruturar e comparar — especialista para decidir.**
