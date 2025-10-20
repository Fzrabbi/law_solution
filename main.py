import json
import os
from fastapi import FastAPI, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.responses import StreamingResponse
from config import settings
from models import BookkeepingEntry, CustomerSelection, InfoDeskReply
from instruct import sys_instruct_select_customer, sys_instruct_info_desk, sys_instruct_khata_entry
from services import refine_english_markdown,translate_and_format_pdf_with_gemini, generate_docx_from_markdown, extract_text_from_docx
from google import genai
import logging
from io import BytesIO
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi import HTTPException
from fastapi import HTTPException
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = genai.Client(api_key=settings.google_api_key)
app = FastAPI(title='Ankona Service', version='1.0')
app.mount("/static", StaticFiles(directory='static'), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.get("/")
async def serve_frontend():
    # In a real setup, you would typically use something like Jinja2
    # templates or a dedicated route, but serving the static file is easiest:
    from starlette.responses import FileResponse
    return FileResponse("static/ai_legal_converter.html")



@app.post("/parse-natural-khata-entry/", response_model=BookkeepingEntry)
async def parse_natural_khata_entry(
    input: str = Form(...),
):
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=input,
        config={
            'system_instruction': sys_instruct_khata_entry,
            'temperature': 0.01,
            'response_mime_type': 'application/json',
            'response_schema': BookkeepingEntry,
        },
    )

    return json.loads(response.text)


@app.post("/select-khata-customer/", response_model=CustomerSelection)
async def select_khata_customer(
    input: str = Form(...),
    customer_list: str = Form(...),
):
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=input,
        config={
            'system_instruction': sys_instruct_select_customer.format(customer_list),
            'temperature': 0.01,
            'response_mime_type': 'application/json',
            'response_schema': CustomerSelection,
        },
    )

    return json.loads(response.text)


@app.post("/information-desk/", response_model=InfoDeskReply)
async def information_desk(
    input: str = Form(...),
):
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=input,
        config={
            'system_instruction': sys_instruct_info_desk,
            'temperature': 0.01,
            'response_mime_type': 'application/json',
            'response_schema': InfoDeskReply,
        },
    )

    return json.loads(response.text)


@app.post("/convert-case-file/", tags=["Conversion"])
async def convert_file(file: UploadFile = File(...)):
    """
    Receives a Bangla PDF, translates and formats it to English, and returns a DOCX file.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # 1. Read the file content
    pdf_content = await file.read()
    filename = file.filename
    
    # 2. AI Processing (OCR, Translation, and Formatting)
    # The function handles all exceptions internally
    english_markdown_draft = await translate_and_format_pdf_with_gemini(pdf_content, filename)
    # english_markdown_draft = '## Translated Legal Document: Arrest Warrant and First Information Report\n\n**Page 1**\n\n```\nবাংলাদেশ অনলিপি স্ট্যা\nএক\nটাকা\nবাংলাদেশ\nকোর্ট ফি\n```\n\nBangladesh Copy Stamp\nOne\nTaka\nBangladesh\nCourt Fee\n\n10/02/25, 11/02/25, 12/02/25, 22/2/24. 22/02/20\nCriminal: Copy 4-654/25\n\n```\nআদালত\nOURT OF THE CHIEF METROPOLITAN HAG\nসিলেট\n*\n*COPWING DEPARTMEN\nনকল বিভাগ\n```\n\nCourt\nCourt of the Chief Metropolitan Magistrate\nSylhet\n*\n*Copying Department\nCopy Department\n\nGovernment of the People\'s Republic of Bangladesh\nLearned Metropolitan Magistrate, 2nd Court, Sylhet.\nAirport G.R. Case No.-432/2023 AD.\nReference:- Airport Police Station Case No. 05, Date-15/06/2023 AD,\n\n**ARREST WARRANT**\n(Section 75 of the Code of Criminal Procedure)\n\n1) The name and designation of the person or persons to whom this warrant is to be executed.\n\nTo\nOfficer-in-Charge\nShahparan Police Station,\nSMP, Sylhet.\nAccused:- Sajidur Rahman Shaju (28) Father-Md. Aang Mukit Residing- Hatimbag, Police Station-Shahparan, SMP, Sylhet.--To Resident\n\nSignature (Placeholder for signature)\n\n2) Description of the offense.\n2) A complaint has been filed against the above-mentioned accused Sajidur Rahman Shaju under Sections 144/147/148/149/186/332/333/353/307/506 of the Penal Code 1860, along with Section 4 of the Explosive Substances Act 1908. Therefore, you are hereby ordered to apprehend the accused and produce him before me. Let there be no default in this.\n\nSd./Illegible\nMetropolitan Magistrate 2nd Court,\nSylhet.\n\n---\n\nChecked and verified\n(Handwritten Signature: Hare Rahim)\nIn cooperation with.\nVerification Assistant\nDate\n\nCertified to be a true copy\n(Handwritten Signature: Md. Azad Mia)\n(Md. Azad Mia)\nCertifying Officer (In-Charge) Copying Department (Nazir)\nMetropolitan Magistrate Court, Sylhet.\nLaw 73 that, former minister.\n\n"Take an oath of patriotism, bid farewell to corruption"\n\n---\n\n**Page 2**\n\n```\nবাংলাদেশ অনুলিপি ষ্ট্যান্ড\nএক\nটাকা\nবাংলাদেশ\nকোর্ট ফি\n```\n\nBangladesh Copy Stamp\nOne\nTaka\nBangladesh\nCourt Fee\n\n10/02/25, 11/02/25, 12/02/25, 22/0/20. 240/202.\nCriminal: Copy:-654/25\nB.P. Form No.-27\nBangladesh Form No.-5356\n\n```\nমেট্রোপলিটন ম্যাজিস্ট্রেট আদালত\nRT OF THE CHIEF METROPOLITAN MAGISTRAT\n*\n*COPYING DEPARTMENT\nনকল বিভাগ\n```\n\nMetropolitan Magistrate Court\nCourt of the Chief Metropolitan Magistrate\n*\n*Copying Department\nCopy Department\n\n**FIRST INFORMATION REPORT**\n\nPreliminary Information regarding Cognizable Offenses presented at the Police Station under Section 154 of the Code of Criminal Procedure\n\nSeen by\nSd.) Illegible\nAddl. Chief Metropolitan Magistrate Court,\nSylhet,\n\nUpazila-Airport Police Station\nDistrict: SMP Sylhet.\nCase No. 432\nDate and time of incident: 15/06/2023 AD: Approximately 01:45 AM\n\n**AIRPORT G.R. CASE NO.-432/2023 ENGLISH.**\n\nDate and time of presentation: 15/06/2023 AD, 21:05 PM.\nPlace of incident, distance and direction from police station and responsible area no.-\nPlace of incident: On Sylhet Bholaganj Road, in front of Sylhet Divisional Stadium under Airport Police Station. Distance from police station approximately 03 km west. AmbarKhana Police Outpost, Beat No.-03.\n\nDate of dispatch from police station: 16/06/2023 AD.\n\nN.B.:- The preliminary information must contain the signature or thumb impression of the informant and be attested by the recording officer.\n\nName and residential address of informant and complainant:\nS.I., Asim Kumar Sarkar, Airport Police Station, SMP, Sylhet.\n\nName and residential address of accused:\n1. Rezaul Hasan Koyes Lodi (50) Father-Unknown, Residing-Housing Estate, Upazila-Police Station-Airport, Sylhet,\n2. Dr. Nazmul Islam (48) Father-Abdul Karim, House No.-18, Police Station-Kotwali, Sylhet\n3. Shakil (25) Father-Sirjan alias Siraj Mia Village-Khuliyapara,\n\n"Take an oath of patriotism, bid farewell to corruption"\n\n---\n\n**Page 3**\n\n```\nবাংলাদেশ অনুলিপি ষ্ট্যাম্প\nটাকা\n```\n\nBangladesh Copy Stamp\nTaka\n\n(2)\n\n```\nHE CHIEF METROPOLITAN MAGISTRAথানা-কতোয়ালী, সিলেট ৪। শামীম (১৮) পিতা-সিরজান ওরফে\nপ্লটন ম্যাজিস্ট্রেট আদালত\nমেট্রোপলিটন\nOF TH\n*\n**\n* COPYING DEPARTMEN\nনকল বিভাগ\n```\n\nPolice Station-Kotwali, Sylhet 4. Shamim (18) Father-Sirjan alias\nMetropolitan Magistrate Court\nOf The Chief Metropolitan Magistrate\n*\n**\n*Copying Department\nCopy Department\n\nSiraj Mia, Residing-Khuliyapara Police Station-Kotwali, Sylhet, 5. Sujan (25) Father-Gedu Mia, currently-Khuliyapara, House No.-11/1) Upazila/Police Station-Kotwali, Sylhet 7. Delwar Hossain Dinar (Haji Dinar) (35), Father-Unknown, Village-Teroroton, Sylhet, 8. Enamul Haque (30), 9. Ekramul Haque (22), both Father-Abdul Bari, both Village-Shahjalal Upashahar, Sylhet, 10. Humayun Ahmed (56), Father-Late Kabir Ahmed, Permanent Village-Dashghar, Police Station-Bishwanath, District-Sylhet, Currently-Shahjalal Upashahar, House No.-32, Main Road, 11. Md. Sabbir Ahmed Dinar (33), Father-Akteruzzaman, Residing-17/1, Momtaz Villa, Purbo Chowkidekhi, AmbarKhana, Police Station-Airport, 12. Solid (36), Father-Unknown, Village-Upashahar, 13. Forhad (28), Father-Unknown, Village-Teroroton, 14. Saddam (30), Father-Unknown, Village-Teroroton, 15. Muhibur Rahman Khan Rasel (33), Father-Motiur Rahman Khan, Village-Khan Complex Sonarpara Main Road, Sylhet, 16. Rasel alias Kala Rasel (32), Father-Unknown, Village-House No.-8, Road No.-30, Block/D, Shahjalal Upashahar, Sylhet, 17. Arafat (33), Father-Unknown, Village-Shahjalal Upashahar, Sylhet, 18. Mofazzal Chowdhury Morshed (27), Father-Unknown, Village-Shahjalal Upashahar, Sylhet, 19. Alfu Mia (30), Father-Abdul Haque, Permanent-Village-Tatikona, Upazila/Police Station-Chhatak, Sunamganj, Currently-Village-Teroroton, 20. Shaheen (27), Father-Unknown, Village-Jindabazar Panchbhai Restaurant owner, 21. Sufian (30), Father-Unknown, Village-Upashahar, Business Address-Kalighat, Sylhet, 22. Nazrul alias Junior Nazrul (24), Father-\n\n"Take an oath of patriotism, bid farewell to corruption"\n\n---\n\n**Page 4**\n\n```\n>বাংলাদেশ অনুলিপি ষ্ট্যাম্প\nঢাক\n```\n\n>Bangladesh Copy Stamp\nDhaka\n\n```\nLE CHIEF METROPOLITAN MAGIST\nটাকা\n```\n\nThe Chief Metropolitan Magistrate\nTaka\n\n(3)\n\n```\nমেট্রোপলিটন ম্যাজিস্ট্রেট আদালত অজ্ঞাত, গ্রাম-রায়নগর, সিলেট, ২৪। আফজল (৩০), পিতা-অজ্ঞাত,\nঅজ্ঞাত, গ্রাম-শাহজালাল উপশহর, সিলেট। ২৩ । তোহা (২৮), পিতা-\nচীফ\nCOURT OF\n*\n☆☆\n* COPYING DEPARTMENT\nনকল বিভাগ\n```\n\nMetropolitan Magistrate Court Unknown, Village-Shahjalal Upashahar, Sylhet. 23. Toha (28), Father-Unknown, Village-Raynagar, Sylhet, 24. Afzal (30), Father-Unknown,\nChief\nCourt of\n*\n☆☆\n*Copying Department\nCopy Department\n\nVillage-Bianibazar, Sylhet, 25. Imad Uddin Ayman (45) Father-Unknown, Residing-Dashghar, P.O. Dashghar, Police Station-Bishwanath, District-Sylhet (Organizational Secretary, Ward No. 8, Dashghar UP, Bishwanath) 26. Sadikur Rahman (24), Father: Md. Kaptan Mia, Residing: Kalatikar, Nipabon A/A Road, Khadimpara, Police Station: Shahparan (R.), District: Sylhet, 27. Saber (30), Father: Unknown, Residing: Hawapara, All Police Station: Kotwali, 28. Osman Ghani (30), Father Unknown, Residing: Pathantula, Police Station Jalalabad, 29. Rashid (30), Father Unknown, Residing: Shibganj, Police Station: Shahparan (R.), 30. Sajidur Rahman Shaju (28) Father-Md. Aang Mukit Residing-Hatimbag, Police Station-Shahparan, All District-Sylhet, along with 20/30 unknown unruly BNP, Chhatra Dal, Juba Dal activists.\n\n**Brief description of offenses and seized articles with sections:**\nSections:- 144/147/148/149/186/332/333/353/307/506 of the Penal Code 1860, along with Section 4 of the Explosive Substances Act 1908.\n\nItems seized upon recovery: 10 iron rods, 08 bamboo sticks, 40 pieces of bricks of various sizes, 02 machetes, 03 unexploded cocktail-like objects.\n\n**Explanation for promptness of investigation and delay in recording information:**\nUpon receiving the computer-typed complaint from the plaintiff at the police station, I duly filled out the preliminary information column and registered this case. A note has been made in the ledger. Discussion has taken place with higher authorities prior to the registration of the case. The complaint is considered an FIR and is attached herewith.\n\n"Take an oath of patriotism, bid farewell to corruption"\n\n---\n\n**Page 5**\n\n```\nবাংলাদেশ অনালিপি স্ট্যা\nএক\nটাকা\nই টাকা\n```\n\nBangladesh Copy Stamp\nOne\nTaka\nTwo Taka\n\n(4)\n\n```\nমেট্রোপলিটন ম্যাজিস্ট্রেট আদালত\nTHE CHIEF METROPOLITAN MAGISTRA মামলা তদন্তের ব্যবস্থা করিবেন।\nOF T\n*\n*\n* COPYING DEPARTMENT ★\nনকল বিভাগ\n```\n\nMetropolitan Magistrate Court\nThe Chief Metropolitan Magistrate\n*\n*\n*Copying Department ★\nCopy Department\n\ndid. The reason for delay is mentioned in the FIR. The Police Inspector (Investigation) will arrange for the investigation of the case.\n\nCase Outcome: X\n\nNote:- The signature or thumb impression of the informant must be present at the bottom of the information.\n\nTo,\nOfficer-in-Charge\nAirport Police Station\nSMP Sylhet.\n\nSubject: FIR.\n\nSir,\n\nHumbly submitted that,\n\nI, S.I., Asim Kumar Sarkar, Airport Police Station, SMP, Sylhet, am present at the police station and am lodging this complaint to the effect that during the nationwide blockade called by BNP and the 20-party alliance, demanding elections under a non-partisan neutral caretaker government, the aforementioned defendants along with 20/30 other unknown BNP activists were obstructing the road at the aforementioned spot, creating impediments to vehicular movement and vandalizing vehicles while shouting slogans like "blockade is on, blockade will continue".\n\nUpon receiving the said news, the Deputy Police Commissioner (North), Senior Assistant Police Commissioner, SMP Sylhet, and the Officer-in-Charge, Airport Police Station, SMP Sylhet, along with duty parties in various locations in this police station area, reached the mentioned spot at 01:35 AM on 15/06/2023 AD. When asked to calm down, the unruly BNP activists became further agitated and threw bricks, stones, and cocktails at the police. The bricks thrown by the accused\n\n"Take an oath of patriotism, bid farewell to corruption"\n\n---\n\n**Page 6**\n\n```\nবাংলাদেশ অনুলিপি স্ট্যাম্প\n```\n\nBangladesh Copy Stamp\n\n```\nলিটন ম্যাজিস্ট্রেট আদ\nOF THE CHIEF METROPOLITAN MAGISTR\n(\nCOURT OF\n*\n* COPYING DEPARTMENT\nনকল বিভাগ\n```\n\nMetropolitan Magistrate\nOf The Chief Metropolitan Magistrate\n(\nCourt of\n*\n*Copying Department\nCopy Department\n\nTaka\n\nbricks and stones injured ASI Khorshed Alam, Constable/1560 Sanjay and Constable/1787 Enamul Haque. When the police chased the BNP activists, they dispersed and fled in various directions. At that time, accused Nos. 1-4 were apprehended, and other accused fled. From the possession of accused No. 1, 1 hockey stick, from accused No. 2, 1 bamboo stick, from accused No. 3, 1 bamboo stick, and from accused No. 4, 3 cocktail-like objects, which were found scattered at the scene.\n\nThereafter, from the scene, 1 Glamour motorcycle, registration No.-Sylhet H-14-4918, 2. one Hero motorcycle, registration No.-Sylhet H-15-1364, 3. one Glamour motorcycle, registration No.-Sylhet H-13-6419, and 03 unexploded cocktail-like objects thrown at the police were recovered. All seized items and arrested accused were taken into custody based on the seizure list prepared in front of witnesses at 13:50 on 15/06/2023 AD.\n\nSubsequently, the injured police personnel were taken to Sylhet MAG Osmani Medical College Hospital for preliminary treatment. The accused, as members of an unlawful assembly, joined the riot with dangerous local weapons, obstructed police in their official duties, assaulted police personnel with intent to murder, causing simple injury, intimidation, and damage to life and property by storing and throwing explosive substances, thereby committing offenses under Sections 143/147/148/149/186/332/353/307/506 of the Penal Code 1860, along with Section 4 of the Explosive Substances Act 1908.\n\nCollecting the names and addresses of the absconding accused, conducting raids in various places to apprehend them, and discussing the matter with higher authorities caused some delay in coming to the police station and lodging the FIR.\n\n"Take an oath of patriotism, bid farewell to corruption"\n\n---\n\n**Page 7**\n\n```\n২\nবাংলাদেশ অনুলিপি ষ্ট্যান্ড\nএক\nটাকা\nদুই টাকা\n```\n\n2\nBangladesh Copy Stamp\nOne\nTaka\nTwo Taka\n\n```\nবাংলাদেশ\nকোর্ট ফি\n```\n\nBangladesh\nCourt Fee\n\n```\nপলিটন ম্যাজিস্ট্রেট আদালত\nTHE CHIEF METROPOLITAN MAGISTRATE\nমেট্রোপ\n*\n*(*\n* COPYING DEPARTMENT\nনকল বিভাগ\n```\n\nMetropolitan Magistrate Court\nThe Chief Metropolitan Magistrate\n*\n*(*\n*Copying Department\nCopy Department\n\nTherefore, Sir, may it please you to register a regular case against the arrested and absconding accused under the mentioned sections and take legal action.\n\nAttached :- 1. Seizure List 01 page.\n\nRespectfully,\nSd: Illegible\nAsim Kumar Sarkar\n(S.I. (Inv.))\nAirport Police Station,\nSMP Sylhet.\n\n---\n\nChecked and verified\n(Handwritten Signature: Atave Rahn)\nIn cooperation with.\nVerification Assistant\nDate\n\nCertified to be a true copy\n(Handwritten Signature: Md. Azad Mia)\n(Md. Azad Mia)\nCertifying Officer (In-Charge) Copying Department (Nazir)\nMetropolitan Magistrate Court, Sylhet.\n109 10th said 76 section he former power.\n\n"Take an oath of patriotism, bid farewell to corruption"'
    
    # 3. AI Refinement (Pass sample content for style context)
    sample_content = None
    sample_file_name = "style_reference.docx"
    sample_file_path = os.path.join(os.getcwd(), sample_file_name)

    if os.path.exists(sample_file_path):
        print(f"Reading local sample DOCX file for style: {sample_file_path}")
        try:
            with open(sample_file_path, "rb") as f:
                docx_content = f.read()
            # Extract text from the binary DOCX content
            sample_text_content = extract_text_from_docx(docx_content)
            
            if not sample_text_content:
                 print(f"Warning: DOCX file '{sample_file_name}' was found but yielded no extractable text. Skipping style reference.")
                 
        except Exception as e:
            # Continue without the sample if reading or extraction fails
            print(f"Warning: Could not process local sample file '{sample_file_name}': {e}")
            sample_text_content = None # Ensure content is None on failure

    english_markdown = await refine_english_markdown(english_markdown_draft, sample_content)
    # 4. DOCX Generation
    doc_buffer = generate_docx_from_markdown(english_markdown)
    
    # 5. Return the DOCX file
    docx_filename = filename.replace(".pdf", "_Translated.docx")
    
    # Use a temporary file to hold the data
    output_path = os.path.join(os.getcwd(), docx_filename)
    
    # 6. Write the in-memory buffer to the permanent file path
    with open(output_path, "wb") as f:
        f.write(doc_buffer.getvalue())
    # 7. Return the file using FileResponse
    # The 'background=...' ensures the temporary file is deleted after the response is sent.
    print(f"File successfully saved to: {output_path}")
    return FileResponse(
        path=output_path,
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        filename=docx_filename,
        # IMPORTANT: Removed the 'background=os.remove(tmp_path)' argument
        # The file will now remain in your project root.
    )