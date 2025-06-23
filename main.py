from flask import Flask, render_template, request, redirect, url_for
import pandas as pd

app = Flask(__name__)
app.secret_key = 'supersecretkey'
DATA_FILE = 'ARANDANOS.xlsx'

# Carga de datos
df_energia = pd.read_excel(DATA_FILE, sheet_name="DATOS")
df_prod = pd.read_excel(DATA_FILE, sheet_name="PRODUCCION")
df_energia.columns = df_energia.columns.str.strip()
df_prod.columns = df_prod.columns.str.strip()

# Jerarquía de procesos y equipos
procesos_vars = [
    ("CAMARAFRIO", "Cámara Frío"),
    ("CLIMATIZACION", "Climatización"),
    ("TUNELESMP", "Túneles MP"),
    ("TUNELPT", "Túnel PT"),
    ("ARANDANOSSUMATORIAPROCESO", "Proceso"),
]
procesos_equipos_dict = {
    "CAMARAFRIO": [
        ("UVACAMARADEFRIO01", "Uva Cámara Frío 01"),
        ("UVACAMARADEFRIO02", "Uva Cámara Frío 02"),
        ("UVACAMARADEFRIO03", "Uva Cámara Frío 03"),
    ],
    "CLIMATIZACION": [
        ("UNIDADCONDENSADORA01", "Unidad Condensadora 01"),
        ("UNIDADCONDENSADORA02", "Unidad Condensadora 02"),
        ("UNIDADCONDENSADORA03", "Unidad Condensadora 03"),
        ("UNIDADCONDENSADORA04", "Unidad Condensadora 04"),
    ],
    "TUNELESMP": [
        ("TUNEL01MT", "Túnel 01 MT"),
        ("TUNEL02MT", "Túnel 02 MT"),
        ("TUNEL03MT", "Túnel 03 MT"),
    ],
    "TUNELPT": [
        ("TUNELINDIVIDUAL", "Túnel Individual"),
        ("TUNEL04", "Túnel 04"),
        ("TUNEL05", "Túnel 05"),
        ("TUNEL06", "Túnel 06"),
        ("TUNEL07", "Túnel 07"),
        ("TUNEL08", "Túnel 08"),
        ("TUNEL09", "Túnel 09"),
        ("TUNEL10", "Túnel 10"),
    ],
    "ARANDANOSSUMATORIAPROCESO": [
        ("ARANDANOSDUALKATO01", "Dual Kato 01"),
        ("ARANDANOSDUALKATO02", "Dual Kato 02"),
    ]
}
planta_vars = [("PLANTAGENERAL", "BETA ICA")
               ]  # Cambié "Planta General" por "BETA ICA"


def get_columns(base):
    return {"kWh": f"{base}(kWh)", "kW": f"{base}(kW)", "FP": f"FP{base}(%)"}


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/seleccion", methods=["POST"])
def seleccion():
    proceso = request.form.get("proceso", "")
    if proceso == "congelados":
        return redirect(url_for("subir_congelados"))
    if proceso == "arandanos":
        return redirect(url_for("dashboard_arandanos"))
    return redirect(url_for("home"))


from flask import request, make_response
from weasyprint import HTML


@app.route("/arandanos")
def dashboard_arandanos():
    # ---- Parámetros de la URL (filtros) ----
    nivel = request.args.get("nivel", "PLANTA")
    unidad = request.args.get("unidad", "kg")
    proceso = request.args.get("proceso", "")
    equipo = request.args.get("equipo", "")
    indicador = request.args.get("indicador", planta_vars[0][0])
    min_fecha = str(df_energia['FECHA'].min())
    max_fecha = str(df_energia['FECHA'].max())
    fecha_inicio = pd.to_datetime(request.args.get("fecha_inicio",
                                                   min_fecha)).date()
    fecha_fin = pd.to_datetime(request.args.get("fecha_fin", max_fecha)).date()

    # ---- Jerarquía y lógica de selección ----
    if nivel == "PLANTA":
        indicador = request.args.get("indicador", planta_vars[0][0])
        nombre = dict(planta_vars).get(indicador, planta_vars[0][1])
        base = indicador
        equipos_this = []
    elif nivel == "PROCESO":
        proceso = request.args.get("proceso", procesos_vars[0][0])
        nombre = dict(procesos_vars).get(proceso, procesos_vars[0][1])
        equipos_this = procesos_equipos_dict.get(proceso, [])
        equipo = request.args.get("equipo", "")
        if equipo and any(e[0] == equipo for e in equipos_this):
            base = equipo
            nombre += " - " + dict(equipos_this)[equipo]
        else:
            base = proceso
    else:
        # Para "EQUIPO", puedes personalizar más si tuvieras muchos equipos sueltos.
        base = request.args.get("indicador", "")
        nombre = base
        equipos_this = []

    cols = get_columns(base)

    # ---- Filtrado por fecha ----
    df_energia['FECHA'] = pd.to_datetime(df_energia['FECHA']).dt.date
    df_prod['FECHA'] = pd.to_datetime(df_prod['FECHA']).dt.date
    mask_energia = (df_energia['FECHA'] >= fecha_inicio) & (df_energia['FECHA']
                                                            <= fecha_fin)
    mask_prod = (df_prod['FECHA'] >= fecha_inicio) & (df_prod['FECHA']
                                                      <= fecha_fin)
    energia_filtrada = df_energia.loc[mask_energia]
    prod_filtrada = df_prod.loc[mask_prod]

    # ---- Cálculo diario ----
    energia_dia = (energia_filtrada.groupby('FECHA')[cols["kWh"]].agg(
        lambda x: x.iloc[-1] - x.iloc[0]) if cols["kWh"]
                   in energia_filtrada.columns else pd.Series(dtype='float'))
    potencia_dia = (energia_filtrada.groupby('FECHA')[cols["kW"]].mean()
                    if cols["kW"] in energia_filtrada.columns else pd.Series(
                        dtype='float'))
    fp_dia = (energia_filtrada.groupby('FECHA')[cols["FP"]].mean()
              if cols["FP"] in energia_filtrada.columns else pd.Series(
                  dtype='float'))
    prod_dia = (prod_filtrada.groupby('FECHA')['KG PROCESADOS'].sum()
                if 'KG PROCESADOS' in prod_filtrada.columns else pd.Series(
                    dtype='float'))

    # ---- Resúmenes y totales ----
    suma_proc = prod_filtrada['KG PROCESADOS'].sum(
    ) if 'KG PROCESADOS' in prod_filtrada else 0
    suma_ing = prod_filtrada['KG INGRESADOS'].sum(
    ) if 'KG INGRESADOS' in prod_filtrada else 0
    presentacion = prod_filtrada['PRESENTACION'].iat[
        0] if not prod_filtrada.empty else ""
    variedad = prod_filtrada['VARIEDAD'].iat[
        0] if not prod_filtrada.empty else ""

    # ---- Conversión a toneladas ----
    if unidad == "ton":
        prod_dia = prod_dia / 1000
        suma_proc = suma_proc / 1000
        suma_ing = suma_ing / 1000

    # ---- DataFrame para tablas y gráficos ----
    df_graf = pd.DataFrame({'FECHA': energia_dia.index})
    df_graf['ENERGIA'] = energia_dia.values
    df_graf['POTENCIA'] = potencia_dia.reindex(energia_dia.index,
                                               fill_value=0).values
    df_graf['FP'] = fp_dia.reindex(energia_dia.index, fill_value=0).values
    df_graf['PRODUCCION'] = prod_dia.reindex(energia_dia.index,
                                             fill_value=0).values
    df_graf = df_graf.fillna(0)
    df_graf['FECHA'] = df_graf['FECHA'].astype(str)

    # Para scatter de correlación:
    scatter_energia_prod = [{
        'x': float(prod),
        'y': float(ene)
    } for prod, ene in zip(df_graf['PRODUCCION'], df_graf['ENERGIA'])]
    scatter_potencia_prod = [{
        'x': float(prod),
        'y': float(pot)
    } for prod, pot in zip(df_graf['PRODUCCION'], df_graf['POTENCIA'])]

    # Tabla
    df_tabla = df_graf.rename(
        columns={
            "FECHA": "FECHA",
            "ENERGIA": "kWh",
            "POTENCIA": "kW",
            "FP": "FP",
            "PRODUCCION": "KG"
        })
    for col in ["kWh", "kW", "FP", "KG"]:
        df_tabla[col] = df_tabla[col].round(2)

    # Línea de tendencia para scatter
    def line_fit(points):
        xs = [p['x'] for p in points]
        ys = [p['y'] for p in points]
        if len(xs) < 2:
            return {'slope': 0, 'intercept': 0}
        import numpy as np
        coeffs = np.polyfit(xs, ys, 1) if len(xs) > 1 else [0, 0]
        return {'slope': coeffs[0], 'intercept': coeffs[1]}

    fit_energia = line_fit(scatter_energia_prod)
    fit_potencia = line_fit(scatter_potencia_prod)

    return render_template(
        "arandanos.html",
        nivel=nivel,
        indicador=indicador,
        proceso=proceso,
        equipo=equipo,
        nombre=nombre,
        planta_vars=planta_vars,
        procesos_vars=procesos_vars,
        procesos_equipos_dict=procesos_equipos_dict,
        equipos_this=equipos_this,
        unidad=unidad,
        min_fecha=min_fecha,
        max_fecha=max_fecha,
        fecha_inicio=str(fecha_inicio),
        fecha_fin=str(fecha_fin),
        suma_kg_procesados=suma_proc,
        suma_kg_ingresados=suma_ing,
        presentacion=presentacion,
        variedad=variedad,
        df=df_tabla.to_dict(orient="records"),
        fechas=df_graf['FECHA'].tolist(),
        prod_dia=df_graf['PRODUCCION'].tolist(),
        energia_dia=df_graf['ENERGIA'].tolist(),
        potencia_dia=df_graf['POTENCIA'].tolist(),
        fp_dia=df_graf['FP'].tolist(),
        scatter_energia_prod=scatter_energia_prod,
        scatter_potencia_prod=scatter_potencia_prod,
        fit_energia=fit_energia,
        fit_potencia=fit_potencia,
    )


from flask import request, make_response
from weasyprint import HTML
import pandas as pd


@app.route("/exportar_pdf", methods=["POST"])
def exportar_pdf():
    dashboard_html = request.form.get("pdf_html", "")
    if not dashboard_html:
        return "No hay datos para exportar.", 400

    logo_url = "https://cdn.prod.website-files.com/65d239c529f6f9c10f1b228a/6608358c6e37447b5b3242ca_beta.png"
    import pytz
    from datetime import datetime
    hora_peru = datetime.now(pytz.timezone("America/Lima"))
    fecha_actual = hora_peru.strftime("%Y-%m-%d %H:%M")

    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>Reporte Dashboard Arándanos</title>
      <style>
        body {{ font-family: Montserrat, Arial, sans-serif; background: #fff; }}
        .container {{ max-width: 1100px; margin: 20px auto; box-shadow:0 0 18px #0002; border-radius: 24px; padding: 30px 36px 30px 36px; }}
        .logo-header {{ text-align:center; margin-bottom: 18px; }}
        .logo-header img {{ max-width: 230px; margin-bottom: 10px; }}
        .fecha-export {{ text-align: right; font-size: 0.95em; color: #477650; margin-bottom: 14px; }}
        h1, h2, h3, h4, h5 {{ color: #237c44; margin-top: 0.4em; margin-bottom: 0.6em; }}
        table {{ width: 100%; border-collapse: collapse; margin: 18px 0 24px 0; }}
        th, td {{ border: 1px solid #caf5db; padding: 7px 10px; text-align: center; }}
        th {{ background: #e4fbe7; color: #218451; font-weight: bold; }}
        td {{ background: #f7fff7; }}
        .resumen {{ background: #eafaf2; border-radius: 18px; padding: 16px 18px; margin: 22px 0 26px 0; display: flex; flex-wrap: wrap; gap: 30px; justify-content: center; }}
        .res-box {{ min-width: 120px; text-align: center; }}
        .res-box .label {{ font-weight: 700; color: #33715a; }}
        .res-box .valor {{ font-size: 1.12em; color: #332; margin-top: 3px; }}
        img {{ max-width: 100%; border-radius: 10px; box-shadow: 0 1px 10px #0002; margin: 12px 0; }}
      </style>
    </head>
    <body>
      <div class="logo-header">
        <img src="{logo_url}" alt="Logo Beta"/>
        <div class="fecha-export">Exportado: {fecha_actual}</div>
      </div>
      {dashboard_html}
    </body>
    </html>
    """
    pdf = HTML(string=full_html).write_pdf()
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers[
        'Content-Disposition'] = 'attachment; filename=Dashboard_Arandanos.pdf'
    return response


if __name__ == "__main__":
    app.run(debug=True)
