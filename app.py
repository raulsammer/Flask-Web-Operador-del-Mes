from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pandas as pd
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import io
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter
from flask import send_from_directory

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'
login_manager = LoginManager()
login_manager.init_app(app)

# Simulación de base de datos de usuarios
users = {'admin': 'contraseña'}  # Cambia esto por una base de datos real

class User(UserMixin):
    def __init__(self, username):
        self.id = username  # Asegúrate de que 'id' sea único para cada usuario
        self.username = username

    def get_id(self):
        return self.id  # Devuelve el ID del usuario

@login_manager.user_loader
def load_user(username):
    return User(username) if username in users else None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if users.get(username) == password:
            user = User(username)
            login_user(user)
            return redirect(url_for('buscar'))
        else:
            flash('Credenciales incorrectas')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/ver_certificado/<dni>')
@login_required
def ver_certificado(dni):
    # Ruta del certificado
    pdf_path = os.path.join('certificados', f"{dni}_certificate.pdf")
    return send_from_directory(directory='certificados', path=f"{dni}_certificate.pdf")

@app.route('/descargar_certificado/<dni>')
@login_required
def descargar_certificado(dni):
    # Ruta del certificado
    pdf_path = os.path.join('certificados', f"{dni}_certificate.pdf")
    return send_from_directory(directory='certificados', path=f"{dni}_certificate.pdf", as_attachment=True)

@app.route('/buscar', methods=['GET', 'POST'])
@login_required
def buscar():
    if request.method == 'POST':
        dni = request.form['dni'].strip()  # Elimina espacios en blanco
        df = pd.read_csv('reg_ope_mes.csv')  # Lee el archivo CSV

        # Búsqueda del operario por DNI
        operario = df[df['DNI'].astype(str).str.strip().str.lower() == dni.lower()]
        if not operario.empty:
            # Convertimos a dict y añadimos la URL del certificado
            operario_info = operario.to_dict(orient='records')[0]
            return render_template('buscar.html', operario=operario_info)
        else:
            flash('DNI no encontrado en la hoja reg_ope_mes.csv')
    return render_template('buscar.html')

@app.route('/agregar', methods=['GET', 'POST'])
@login_required
def agregar():
    if request.method == 'POST':
        dni = request.form['dni'].strip()  # Elimina espacios en blanco
        
        # Imprimir el DNI recibido para depuración
        print(f"DNI recibido: '{dni}'")

        # Leer la base de datos para obtener el nombre y apellidos del operario seleccionado
        df_bbdd = pd.read_csv('bbdd.csv')

        # Imprimir todo el DataFrame para depuración
        print("Datos en bbdd.csv:")
        print(df_bbdd)

        # Filtrar por DNI, asegurando que ambos sean tratados como cadenas
        operario_seleccionado = df_bbdd[df_bbdd['DNI'].astype(str).str.strip() == dni]

        # Verificar si se encontró el operario
        if operario_seleccionado.empty:
            flash('Operario no encontrado en la base de datos.')
            return redirect(url_for('agregar'))

        # Si se encontró, tomar el primer registro
        operario_seleccionado = operario_seleccionado.iloc[0]

        mes_certificado = request.form.get('mes_certificado', '').strip()
        año_certificado = request.form.get('año_certificado', '').strip()

        id_certificado = f"{dni}{mes_certificado[0].upper()}{año_certificado[-2:]}"  # Formato: DNI + inicial del mes + últimos 2 dígitos del año

        # Crear un nuevo registro para reg_ope_mes.csv
        new_row_reg = pd.DataFrame({
            'DNI': [dni],
            'Nombre': [operario_seleccionado['Nombre']],
            'Apellidos': [operario_seleccionado['Apellidos']],
            'id_certificado': [id_certificado],  # Dejar vacío por ahora QUE ME GENERE
            'mes_certificado': [mes_certificado],  # Dejar vacío por ahora QUE HAYA UN BOTON PARA SELECCIONAR MES
            'certificado': [''],  # Dejar vacío por ahora QUE SE MUESTRE O SE SUBA A UN DRIVE 
            'Año': [año_certificado]  # Dejar vacío por ahora QUE SE SELECCION EL AÑO
        })

        # Agregar el nuevo registro a reg_ope_mes.csv usando pd.concat()
        df_reg = pd.read_csv('reg_ope_mes.csv')
        df_reg = pd.concat([df_reg, new_row_reg], ignore_index=True)
        df_reg.to_csv('reg_ope_mes.csv', index=False)

        # Generar el certificado (llamar a la función para generar certificados)
        generar_certificado(dni, operario_seleccionado['Nombre'], operario_seleccionado['Apellidos'], mes_certificado, año_certificado)

        flash(f'Operario {operario_seleccionado["Nombre"]} agregado exitosamente.')
        return redirect(url_for('agregar'))
    
    return render_template('agregar.html')

def generar_certificado(dni, nombre, apellido, mes, año):
    # Configuración de rutas
    output_dir = 'certificados'

    # Crear la carpeta de salida si no existe
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Crear el PDF del certificado
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)

    nombreApellido = f"{apellido.upper()}, {nombre.upper()}"
    mesAño = mes +", " + año
    
    c.setFont('Helvetica-Bold', 20)
    c.drawCentredString(400, 330, nombreApellido)
    
    c.setFont('Helvetica', 15)
    c.drawCentredString(240, 140, mesAño)  # Aquí puedes agregar mes y año si tienes esa información

    c.save()

    # Guardar el PDF final
    packet.seek(0)
    existing_pdf_path = "Reconocimiento_Operador_del_Mes_-_Construcción.pdf"  # Ruta del template PDF
    existing_pdf = PdfReader(open(existing_pdf_path, "rb"))
    
    output_pdf_path = os.path.join(output_dir, f"{dni}_certificate.pdf")
    
    output_pdf = PdfWriter()
    
    page = existing_pdf.pages[0]
    
    new_pdf = PdfReader(packet)
    
    page.merge_page(new_pdf.pages[0])
    
    output_pdf.add_page(page)
    
    with open(output_pdf_path, "wb") as outputStream:
        output_pdf.write(outputStream)

# Nueva ruta para obtener los datos de los operarios en formato JSON para autocompletado.
@app.route('/buscar_operarios', methods=['GET'])
@login_required
def buscar_operarios():
    query = request.args.get('query', '').strip()
    df_bbdd = pd.read_csv('bbdd.csv')
    
    # Filtrar los operarios que coincidan con el DNI ingresado o parte de él.
    filtered_operarios = df_bbdd[df_bbdd['DNI'].astype(str).str.contains(query) | 
                                  df_bbdd['Nombre'].str.contains(query) | 
                                  df_bbdd['Apellidos'].str.contains(query)]
    
    result = filtered_operarios[['DNI', 'Nombre', 'Apellidos']].to_dict(orient='records')
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)