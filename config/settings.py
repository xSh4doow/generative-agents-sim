"""Constantes da simulação."""

LOCATIONS = {
    "praca": "Praça central da vila, com bancos e uma fonte. Ponto de encontro natural.",
    "cafe": "Café Aurora, administrado pela Helena. Serve café, bolo e fofoca.",
    "biblioteca": "Pequena biblioteca com estantes velhas e um cheiro bom de livro.",
    "casa_helena": "Casa da Helena, ao lado do café.",
    "casa_roberto": "Casa do Roberto, cheia de livros empilhados.",
    "casa_camila": "Ateliê-casa da Camila, com telas e tintas por todo lado.",
    "casa_marcos": "Casa do Marcos, organizada e com um mural de planejamento na parede.",
    "casa_julia": "Casa da Júlia e seus pais, quarto cheio de pôsters.",
}

HOURS_PER_DAY = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
NUM_DAYS = 3

# Info-semente: no início do Dia 1, só a Helena sabe.
# Rastrear quantos agentes ficam sabendo ao longo dos 3 dias.
SEED_INFO = "Vai ter uma feira de artesanato no próximo sábado na praça"
SEED_AGENT = "Helena"
SEED_KEYWORDS = ["feira", "artesanato", "sábado", "sabado"]

# Pesos do score de recuperação de memória
RECENCY_WEIGHT = 1.0
RELEVANCE_WEIGHT = 1.0
IMPORTANCE_WEIGHT = 1.0

# Decay de recência: meia-vida em horas de simulação
RECENCY_HALF_LIFE_HOURS = 24

# Trigger de reflexão
REFLECTION_IMPORTANCE_THRESHOLD = 50
REFLECTION_OBSERVATION_THRESHOLD = 8
