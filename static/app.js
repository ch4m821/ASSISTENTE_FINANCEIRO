const mesSelecionado =
    document.getElementById("mesSelecionado");

const dinheiroConta =
    document.getElementById("dinheiroConta");

const reservaBloqueada =
    document.getElementById("reservaBloqueada");

const limiteGasto =
    document.getElementById("limiteGasto");

const listaContas =
    document.getElementById("listaContas");

const aviso =
    document.getElementById("aviso");

const mensagem =
    document.getElementById("mensagem");


const hoje = new Date();

const mesInicial =
    hoje.getFullYear()
    + "-"
    + String(
        hoje.getMonth() + 1
    ).padStart(2, "0");

mesSelecionado.value = mesInicial;


function moeda(valor) {

    return Number(valor).toLocaleString(
        "pt-BR",
        {
            style: "currency",
            currency: "BRL"
        }
    );

}


function mostrarMensagem(texto) {

    mensagem.textContent = texto;

    mensagem.classList.add("mostrar");

    setTimeout(
        () => {
            mensagem.classList.remove(
                "mostrar"
            );
        },
        3000
    );

}


async function requisicao(
    url,
    opcoes = {}
) {

    const resposta =
        await fetch(url, opcoes);

    const dados =
        await resposta.json();

    if (!resposta.ok) {

        throw new Error(
            dados.erro
            || "Erro ao processar solicitação."
        );

    }

    return dados;

}


async function carregarDashboard() {

    try {

        const mes =
            mesSelecionado.value;

        const dados =
            await requisicao(
                `/api/dashboard?mes=${mes}`
            );

        atualizarTela(dados);

    } catch (erro) {

        mostrarMensagem(
            erro.message
        );

    }

}


function atualizarTela(dados) {

    dinheiroConta.value =
        dados.dinheiro_conta;

    reservaBloqueada.value =
        dados.reserva_bloqueada;

    limiteGasto.value =
        dados.limite_gasto;


    document.getElementById(
        "cardDinheiro"
    ).textContent =
        moeda(dados.dinheiro_conta);


    document.getElementById(
        "cardTotal"
    ).textContent =
        moeda(dados.total_contas);


    document.getElementById(
        "cardPago"
    ).textContent =
        moeda(dados.total_pago);


    document.getElementById(
        "cardNaoPago"
    ).textContent =
        moeda(dados.total_nao_pago);


    document.getElementById(
        "cardRestante"
    ).textContent =
        moeda(dados.restante_previsto);


    document.getElementById(
        "cardDisponivel"
    ).textContent =
        moeda(
            dados.disponivel_apos_reserva
        );


    aviso.textContent =
        dados.aviso;

    aviso.className =
        `aviso ${dados.nivel_aviso}`;


    renderizarContas(
        dados.contas
    );

}


function renderizarContas(contas) {

    listaContas.innerHTML = "";


    if (contas.length === 0) {

        listaContas.innerHTML = `
            <tr>
                <td
                    colspan="5"
                    class="sem-contas"
                >
                    Nenhuma conta cadastrada.
                </td>
            </tr>
        `;

        return;

    }


    contas.forEach(
        conta => {

            const linha =
                document.createElement("tr");


            const pago =
                conta.status === "pago";


            const statusTexto =
                pago
                    ? "✅ Pago"
                    : "❌ Não pago";


            const statusClasse =
                pago
                    ? "status-pago"
                    : "status-nao-pago";


            const botaoStatus =
                pago
                    ? `
                        <button
                            class="
                                btn
                                btn-desmarcar
                            "
                            onclick="
                                alterarStatus(
                                    ${conta.id},
                                    'nao_pago'
                                )
                            "
                        >
                            Marcar não pago
                        </button>
                    `
                    : `
                        <button
                            class="
                                btn
                                btn-pagar
                            "
                            onclick="
                                alterarStatus(
                                    ${conta.id},
                                    'pago'
                                )
                            "
                        >
                            Marcar pago
                        </button>
                    `;


            linha.innerHTML = `
                <td>
                    ${escapeHtml(conta.nome)}
                </td>

                <td>
                    ${moeda(conta.valor)}
                </td>

                <td>
                    <span class="tipo">
                        ${
                            conta.tipo === "fixa"
                                ? "Fixa"
                                : "Variável"
                        }
                    </span>
                </td>

                <td>
                    <span
                        class="
                            status
                            ${statusClasse}
                        "
                    >
                        ${statusTexto}
                    </span>
                </td>

                <td>
                    <div class="acoes">

                        ${botaoStatus}

                        <button
                            class="
                                btn
                                btn-excluir
                            "
                            onclick="
                                excluirConta(
                                    ${conta.id}
                                )
                            "
                        >
                            Excluir
                        </button>

                    </div>
                </td>
            `;


            listaContas.appendChild(
                linha
            );

        }
    );

}


function escapeHtml(texto) {

    const elemento =
        document.createElement("div");

    elemento.textContent =
        texto;

    return elemento.innerHTML;

}


document.getElementById(
    "salvarConfiguracao"
).addEventListener(
    "click",
    async () => {

        try {

            const mes =
                mesSelecionado.value;


            const dados =
                await requisicao(
                    `/api/meses/${mes}/configuracoes`,
                    {
                        method: "PUT",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify(
                            {
                                dinheiro_conta:
                                    Number(
                                        dinheiroConta.value
                                    ),

                                reserva_bloqueada:
                                    Number(
                                        reservaBloqueada.value
                                    ),

                                limite_gasto:
                                    Number(
                                        limiteGasto.value
                                    )
                            }
                        )
                    }
                );


            atualizarTela(dados);

            mostrarMensagem(
                "Valores atualizados."
            );

        } catch (erro) {

            mostrarMensagem(
                erro.message
            );

        }

    }
);


document.getElementById(
    "formConta"
).addEventListener(
    "submit",
    async evento => {

        evento.preventDefault();


        const nome =
            document.getElementById(
                "nomeConta"
            ).value;


        const valor =
            document.getElementById(
                "valorConta"
            ).value;


        const tipo =
            document.getElementById(
                "tipoConta"
            ).value;


        try {

            const dados =
                await requisicao(
                    "/api/contas",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify(
                            {
                                mes:
                                    mesSelecionado.value,

                                nome,

                                valor,

                                tipo
                            }
                        )
                    }
                );


            atualizarTela(dados);


            document.getElementById(
                "formConta"
            ).reset();


            mostrarMensagem(
                "Conta adicionada."
            );

        } catch (erro) {

            mostrarMensagem(
                erro.message
            );

        }

    }
);


async function alterarStatus(
    id,
    status
) {

    try {

        const dados =
            await requisicao(
                `/api/contas/${id}/status`,
                {
                    method: "PATCH",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify(
                        {
                            status
                        }
                    )
                }
            );


        atualizarTela(dados);

    } catch (erro) {

        mostrarMensagem(
            erro.message
        );

    }

}


async function excluirConta(id) {

    const confirmar =
        confirm(
            "Deseja realmente excluir esta conta?"
        );


    if (!confirmar) {
        return;
    }


    try {

        const dados =
            await requisicao(
                `/api/contas/${id}`,
                {
                    method: "DELETE"
                }
            );


        atualizarTela(dados);

        mostrarMensagem(
            "Conta excluída."
        );

    } catch (erro) {

        mostrarMensagem(
            erro.message
        );

    }

}


document.getElementById(
    "copiarFixas"
).addEventListener(
    "click",
    async () => {

        try {

            const mes =
                mesSelecionado.value;


            const dados =
                await requisicao(
                    `/api/meses/${mes}/copiar-fixas`,
                    {
                        method: "POST"
                    }
                );


            atualizarTela(dados);


            mostrarMensagem(
                `${dados.contas_copiadas} conta(s) fixa(s) carregada(s).`
            );

        } catch (erro) {

            mostrarMensagem(
                erro.message
            );

        }

    }
);


mesSelecionado.addEventListener(
    "change",
    carregarDashboard
);


carregarDashboard();
