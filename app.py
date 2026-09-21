import streamlit as st
import pandas as pd
import joblib
import requests


# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------

st.set_page_config(
    page_title="Predictor de precios inmobiliarios",
    page_icon="🏠",
    layout="centered"
)


# --------------------------------------------------
# CARGA DEL MODELO Y ARCHIVOS AUXILIARES
# --------------------------------------------------

modelo = joblib.load(
    "modelo_predictor_deploy_v2.pkl"
)

localidades = pd.read_csv(
    "localidades_referencia.csv"
)


# --------------------------------------------------
# FUNCIÓN PARA OBTENER COORDENADAS
# --------------------------------------------------

def obtener_coordenadas(direccion, localidad, zona):

    url = "https://nominatim.openstreetmap.org/search"

    if zona == "Capital Federal":
        zona_busqueda = "Buenos Aires"
    else:
        zona_busqueda = "Provincia de Buenos Aires"

    consultas = [
        f"{direccion}, {localidad}, {zona_busqueda}, Argentina",
        f"{direccion}, {localidad}, Buenos Aires, Argentina",
        f"{direccion}, Buenos Aires, Argentina"
    ]

    headers = {
        "User-Agent": "predictor-inmobiliario-teclab/1.0"
    }

    for consulta in consultas:

        params = {
            "q": consulta,
            "format": "jsonv2",
            "limit": 1,
            "countrycodes": "ar"
        }

        try:
            respuesta = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=10
            )

            respuesta.raise_for_status()

            datos = respuesta.json()

            if datos:
                latitud = float(
                    datos[0]["lat"]
                )

                longitud = float(
                    datos[0]["lon"]
                )

                direccion_encontrada = (
                    datos[0]["display_name"]
                )

                return (
                    latitud,
                    longitud,
                    direccion_encontrada
                )

        except Exception:
            pass

    return None, None, None


# --------------------------------------------------
# TÍTULO
# --------------------------------------------------

st.title(
    "🏠 Predictor de precios inmobiliarios"
)

st.write(
    "Ingresá las características de una propiedad "
    "para obtener una estimación de su precio de venta."
)


# --------------------------------------------------
# UBICACIÓN
# --------------------------------------------------

st.subheader(
    "Ubicación"
)

property_type = st.selectbox(
    "Tipo de propiedad",
    [
        "Seleccionar...",
        "Departamento",
        "Casa",
        "PH"
    ]
)

zonas = sorted(
    localidades["l2"]
    .dropna()
    .unique()
)

l2 = st.selectbox(
    "Zona",
    ["Seleccionar..."] + zonas
)

if l2 != "Seleccionar...":

    localidades_zona = sorted(
        localidades.loc[
            localidades["l2"] == l2,
            "l3"
        ]
        .dropna()
        .unique()
    )

    l3 = st.selectbox(
        "Localidad / barrio",
        ["Seleccionar..."] + localidades_zona
    )

else:

    l3 = st.selectbox(
        "Localidad / barrio",
        ["Seleccionar..."],
        disabled=True
    )

direccion = st.text_input(
    "Dirección exacta (opcional)",
    placeholder="Ej: Alberdi 425"
)


# --------------------------------------------------
# CARACTERÍSTICAS
# --------------------------------------------------

st.subheader(
    "Características de la propiedad"
)

surface_total = st.number_input(
    "Superficie total (m²)",
    min_value=1.0,
    value=None,
    placeholder="Ingresá la superficie total"
)

surface_covered = st.number_input(
    "Superficie cubierta (m²)",
    min_value=1.0,
    value=None,
    placeholder="Ingresá la superficie cubierta"
)

rooms = st.number_input(
    "Ambientes",
    min_value=1,
    value=None,
    placeholder="Ingresá la cantidad de ambientes"
)

bedrooms = st.number_input(
    "Dormitorios",
    min_value=0,
    value=None,
    placeholder="Ingresá la cantidad de dormitorios"
)

bathrooms = st.number_input(
    "Baños",
    min_value=1,
    value=None,
    placeholder="Ingresá la cantidad de baños"
)


# --------------------------------------------------
# BOTÓN DE PREDICCIÓN
# --------------------------------------------------

if st.button(
    "Estimar precio",
    type="primary"
):

    # ----------------------------------------------
    # VALIDACIÓN
    # ----------------------------------------------

    campos_incompletos = (
        property_type == "Seleccionar..."
        or l2 == "Seleccionar..."
        or l3 == "Seleccionar..."
        or surface_total is None
        or surface_covered is None
        or rooms is None
        or bedrooms is None
        or bathrooms is None
    )

    if campos_incompletos:

        st.error(
            "Completá todos los campos obligatorios "
            "antes de estimar."
        )

        st.stop()


    # ----------------------------------------------
    # CARGA Y PREDICCIÓN
    # ----------------------------------------------

    with st.spinner(
        "Buscando ubicación y calculando estimación..."
    ):

        uso_direccion_exacta = False
        direccion_encontrada = None

        ubicacion = localidades[
            (localidades["l2"] == l2)
            &
            (localidades["l3"] == l3)
        ]

        if ubicacion.empty:

            st.error(
                "No se encontró una ubicación de referencia "
                "para la localidad seleccionada."
            )

            st.stop()

        ubicacion = ubicacion.iloc[0]

        latitud = ubicacion["latitud"]
        longitud = ubicacion["longitud"]


        # ------------------------------------------
        # DIRECCIÓN OPCIONAL
        # ------------------------------------------

        if direccion.strip():

            (
                latitud_dir,
                longitud_dir,
                direccion_encontrada
            ) = obtener_coordenadas(
                direccion,
                l3,
                l2
            )

            if (
                latitud_dir is not None
                and longitud_dir is not None
            ):

                latitud = latitud_dir
                longitud = longitud_dir
                uso_direccion_exacta = True

            else:

                st.warning(
                    "No se pudo localizar la dirección exacta. "
                    "Se utilizará la ubicación de referencia "
                    "de la localidad."
                )


        # ------------------------------------------
        # CREAR PROPIEDAD
        # ------------------------------------------

        nueva_propiedad = pd.DataFrame([{
            "surface_total": surface_total,
            "surface_covered": surface_covered,
            "rooms": rooms,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "property_type": property_type,
            "l2": l2,
            "l3": l3,
            "latitud": latitud,
            "longitud": longitud
        }])


        # ------------------------------------------
        # PREDICCIÓN
        # ------------------------------------------

        precio_estimado = modelo.predict(
            nueva_propiedad
        )[0]


    # --------------------------------------------------
    # RESULTADOS
    # --------------------------------------------------

    if uso_direccion_exacta:

        st.info(
            f"📍 Ubicación encontrada: "
            f"{direccion_encontrada}"
        )


    st.subheader(
        "Resumen de la propiedad"
    )

    st.write(
        f"""
        **Tipo:** {property_type}  
        **Zona:** {l2}  
        **Localidad:** {l3}  
        **Superficie total:** {surface_total} m²  
        **Superficie cubierta:** {surface_covered} m²  
        **Ambientes:** {rooms}  
        **Dormitorios:** {bedrooms}  
        **Baños:** {bathrooms}
        """
    )


    st.success(
        f"💰 Precio estimado: "
        f"USD {precio_estimado:,.0f}"
    )


    if uso_direccion_exacta:

        st.caption(
            "La predicción utilizó las coordenadas "
            "obtenidas a partir de la dirección ingresada."
        )

    else:

        st.caption(
            "La predicción utilizó una coordenada "
            "representativa de la localidad seleccionada."
        )


    st.caption(
        "La estimación es orientativa y se basa en patrones "
        "históricos del dataset utilizado para entrenar el modelo."
    )