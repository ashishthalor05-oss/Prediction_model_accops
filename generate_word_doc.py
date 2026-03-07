from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import datetime

doc = Document()

# ── Page margins ──────────────────────────────────────────────────────────────
section = doc.sections[0]
section.top_margin    = Cm(2.5)
section.bottom_margin = Cm(2.5)
section.left_margin   = Cm(2.5)
section.right_margin  = Cm(2.5)

# ── Helper: set paragraph shading ─────────────────────────────────────────────
def shade_paragraph(para, fill_hex):
    pPr = para._p.get_or_add_pPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    pPr.append(shd)

# ── Helper: shade table cell ───────────────────────────────────────────────────
def shade_cell(cell, fill_hex):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement('w:shd')
    shd.set(qn('w:val'),   'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'),  fill_hex)
    tcPr.append(shd)

# ── Helper: styled heading ─────────────────────────────────────────────────────
def add_heading(doc, text, level=1, color='1F3864'):
    p   = doc.add_paragraph()
    run = p.add_run(text)
    run.bold      = True
    run.font.size = Pt(16 if level == 1 else 13 if level == 2 else 11)
    run.font.color.rgb = RGBColor.from_string(color)
    p.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    p.paragraph_format.space_after  = Pt(4)
    return p

# ── Helper: body text ─────────────────────────────────────────────────────────
def add_body(doc, text, bold=False, italic=False, color=None):
    p   = doc.add_paragraph()
    run = p.add_run(text)
    run.bold       = bold
    run.italic     = italic
    run.font.size  = Pt(11)
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    p.paragraph_format.space_after = Pt(4)
    return p

# ── Helper: bullet point ──────────────────────────────────────────────────────
def add_bullet(doc, text, sub=False):
    p   = doc.add_paragraph(style='List Bullet')
    run = p.add_run(text)
    run.font.size = Pt(11)
    p.paragraph_format.left_indent   = Cm(1.5 if sub else 0.8)
    p.paragraph_format.space_after   = Pt(3)
    return p

# ── Helper: simple table ──────────────────────────────────────────────────────
def add_table(doc, headers, rows, header_fill='1F3864', row_fill_alt='EBF0FA'):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Header row
    hdr_row = table.rows[0]
    for i, h in enumerate(headers):
        cell = hdr_row.cells[i]
        cell.text = ''
        run = cell.paragraphs[0].add_run(h)
        run.bold = True
        run.font.color.rgb = RGBColor(255, 255, 255)
        run.font.size = Pt(10.5)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        shade_cell(cell, header_fill)

    # Data rows
    for ri, row_data in enumerate(rows):
        row = table.rows[ri + 1]
        fill = row_fill_alt if ri % 2 == 0 else 'FFFFFF'
        for ci, val in enumerate(row_data):
            cell = row.cells[ci]
            cell.text = ''
            run = cell.paragraphs[0].add_run(str(val))
            run.font.size = Pt(10)
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            shade_cell(cell, fill)

    doc.add_paragraph()
    return table

# ═══════════════════════════════════════════════════════════════════════════════
#  TITLE PAGE
# ═══════════════════════════════════════════════════════════════════════════════
title_para = doc.add_paragraph()
title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
shade_paragraph(title_para, '1F3864')
title_run = title_para.add_run('\nResource Usage Prediction Model\nTechnical Reference Note\n')
title_run.bold = True
title_run.font.size = Pt(22)
title_run.font.color.rgb = RGBColor(255, 255, 255)

sub_para = doc.add_paragraph()
sub_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
shade_paragraph(sub_para, '1F3864')
sub_run = sub_para.add_run('Model Selection Rationale  |  System Requirements  |  Tools\n')
sub_run.font.size = Pt(12)
sub_run.font.color.rgb = RGBColor(180, 200, 240)

date_para = doc.add_paragraph()
date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
shade_paragraph(date_para, '1F3864')
date_run = date_para.add_run(f'\nPrepared: {datetime.date.today().strftime("%B %d, %Y")}\n')
date_run.font.size = Pt(10)
date_run.font.color.rgb = RGBColor(160, 185, 220)

doc.add_paragraph()

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
add_heading(doc, '1. Project Overview', level=1)
add_body(doc,
    'This document outlines the rationale behind the selection of the Random Forest Regressor '
    'as the prediction model for forecasting concurrent resource usage across 15-minute time '
    'intervals. It also covers the system requirements and tools needed to run the full pipeline.')

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — MODEL SELECTION
# ═══════════════════════════════════════════════════════════════════════════════
add_heading(doc, '2. Model Selection — Why Random Forest Regressor?', level=1)
add_body(doc,
    'The prediction pipeline trains two models and evaluates them against each other: '
    'a Baseline (Historical Average) model and a Random Forest Regressor. The model '
    'with the best accuracy on the test set is retained for production forecasting.')

# ── 2.1 Performance Results ────────────────────────────────────────────────────
add_heading(doc, '2.1  Performance Results', level=2)
add_body(doc, 'The following metrics were recorded on the held-out test set (20% of data):')

add_table(doc,
    headers=['Metric', 'Baseline Model', 'Random Forest', 'Improvement'],
    rows=[
        ['MAE  (Mean Absolute Error)',  '3.8091', '0.1325', '96.52% better ✓'],
        ['RMSE (Root Mean Sq. Error)',  '4.7178', '0.3721', '92.11% better ✓'],
    ],
    header_fill='1F3864',
    row_fill_alt='EBF0FA'
)

add_body(doc,
    'A 96.52% reduction in prediction error clearly demonstrates that Random Forest '
    'captures the complex, non-linear patterns in user concurrency data that a simple '
    'historical average model cannot.')

# ── 2.2 Why Random Forest over other models ────────────────────────────────────
add_heading(doc, '2.2  Why Random Forest Over Other Models?', level=2)

comparisons = [
    ('vs. Baseline (Historical Average)',
     'The baseline simply looks up mean values by (DayOfWeek, Hour, IsHoliday). '
     'It cannot capture interactions between features or adapt to recent usage drift. '
     'Random Forest reduced MAE by 96.52% over this approach.'),
    ('vs. Linear Regression',
     'User concurrency data is highly non-linear — demand spikes at specific hours, '
     'days, and around holidays. Linear Regression assumes a linear relationship and '
     'fails to model these sharp peaks. Random Forest handles non-linearity natively '
     'through its ensemble of decision trees.'),
    ('vs. LSTM / Deep Learning',
     'The dataset consists of structured tabular features (Hour, DayOfWeek, IsWeekend, '
     'IsHoliday). Deep learning models require far larger datasets and significant '
     'compute resources for marginal gain on this type of structured input. Random '
     'Forest achieves excellent accuracy with minimal complexity.'),
    ('vs. XGBoost / Gradient Boosting',
     'XGBoost would be the logical next step if further tuning is needed, but adds '
     'hyperparameter complexity and longer training times. Given the 96%+ accuracy '
     'already achieved with Random Forest, XGBoost is not necessary at this stage.'),
    ('vs. ARIMA / Time-Series Models',
     'ARIMA and similar models require strictly stationary time-series data and '
     'struggle with irregular patterns caused by holidays and flexible work schedules. '
     'Random Forest with calendar-based features handles these gracefully without '
     'requiring stationarity assumptions.'),
]

for title, desc in comparisons:
    p = doc.add_paragraph(style='List Bullet')
    run_title = p.add_run(title + ': ')
    run_title.bold = True
    run_title.font.size = Pt(11)
    run_desc = p.add_run(desc)
    run_desc.font.size = Pt(11)
    p.paragraph_format.space_after = Pt(5)

# ── 2.3 Additional Advantages ─────────────────────────────────────────────────
add_heading(doc, '2.3  Additional Advantages of Random Forest', level=2)
advantages = [
    'Feature Importance: Natively provides interpretable feature rankings — Hour and DayOfWeek are confirmed as the top predictors, which validates the model and aids stakeholder communication.',
    'Robustness: As an ensemble of decision trees, it is resistant to overfitting and handles noisy or incomplete data gracefully.',
    'No Feature Scaling Required: Unlike SVM or neural networks, Random Forest does not require normalisation of input features.',
    'Fast Inference: Pre-trained .joblib model files load in milliseconds, making real-time or scheduled predictions practical.',
    'Handles Holiday & Weekend Flags: Boolean features like IsHoliday and IsWeekend are natively supported without encoding overhead.',
]
for adv in advantages:
    add_bullet(doc, adv)

# ── 2.4 Feature Importance ────────────────────────────────────────────────────
add_heading(doc, '2.4  Key Input Features Used', level=2)
add_table(doc,
    headers=['Feature', 'Description', 'Type'],
    rows=[
        ['Hour',              'Hour of the day (0–23)',              'Numeric'],
        ['DayOfWeek',         'Day of the week (0=Mon, 6=Sun)',      'Numeric'],
        ['IsWeekend',         'Flag: Saturday or Sunday',            'Boolean'],
        ['IsHoliday',         'Flag: Public / Mandatory Holiday',    'Boolean'],
        ['IsOptionalHoliday', 'Flag: Optional Holiday',              'Boolean'],
        ['Month',             'Month (1–12)',                        'Numeric'],
        ['Day',               'Day of month (1–31)',                 'Numeric'],
    ]
)

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 3 — SYSTEM REQUIREMENTS
# ═══════════════════════════════════════════════════════════════════════════════
add_heading(doc, '3. System Requirements', level=1)

add_heading(doc, '3.1  Hardware Requirements', level=2)
add_table(doc,
    headers=['Component', 'Minimum', 'Recommended'],
    rows=[
        ['RAM',         '8 GB',            '16 GB (log_data.csv ~150 MB)'],
        ['CPU',         'Dual-core 2 GHz', 'Quad-core+ (RF training is CPU-bound)'],
        ['Disk Space',  '2 GB free',       '5 GB free (models + data + logs)'],
        ['OS',          'Windows 10',      'Windows 10 / 11 (64-bit)'],
    ]
)

add_heading(doc, '3.2  Software Requirements', level=2)
add_table(doc,
    headers=['Software', 'Version', 'Purpose'],
    rows=[
        ['Python',       '3.8 or higher',  'Core runtime environment'],
        ['pandas',       'Latest stable',  'Data loading, CSV I/O, feature engineering'],
        ['numpy',        'Latest stable',  'Numerical operations and array handling'],
        ['scikit-learn', 'Latest stable',  'RandomForestRegressor, train/test split, metrics'],
        ['matplotlib',   'Latest stable',  'Plotting prediction comparisons and profiles'],
        ['joblib',       'Latest stable',  'Saving and loading trained model (.joblib) files'],
    ]
)

add_heading(doc, '3.3  Installation Command', level=2)
add_body(doc, 'Run the following command in a terminal to install all required dependencies:')
p = doc.add_paragraph()
shade_paragraph(p, 'F2F2F2')
run = p.add_run('    pip install pandas numpy scikit-learn matplotlib joblib')
run.font.name = 'Courier New'
run.font.size = Pt(10.5)
run.bold = True
doc.add_paragraph()

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 4 — PIPELINE & FILES
# ═══════════════════════════════════════════════════════════════════════════════
add_heading(doc, '4. Pipeline Scripts & Output Files', level=1)

add_heading(doc, '4.1  Execution Pipeline (In Order)', level=2)
add_table(doc,
    headers=['Step', 'Script', 'Output File(s)', 'Purpose'],
    rows=[
        ['1', 'filter_logs.py',          'login_logs.csv\ndisconnect_logs.csv\nresource_logs.csv',
         'Filter raw log_data.csv into typed event logs'],
        ['2', 'calculate_concurrency.py', 'concurrency_report.csv',
         'Compute 15-min concurrent user counts'],
        ['3', 'data_analysis_and_prep.py','processed_data.csv',
         'Feature engineering for model training'],
        ['4', 'prediction_model.py',      'rf_model_*.joblib\nmodel_metrics.txt',
         'Train & evaluate Random Forest models'],
        ['5', 'predict_future.py',        'prediction_YYYY-MM-DD.csv',
         'Generate future week predictions'],
        ['6', 'simulation.py',            'provisioning_simulation.png\ncost_optimization_report.txt',
         'Simulate resource provisioning scenarios'],
    ]
)

add_heading(doc, '4.2  Run Full Pipeline', level=2)
add_body(doc, 'To execute the complete pipeline end-to-end, run:')
p = doc.add_paragraph()
shade_paragraph(p, 'F2F2F2')
run = p.add_run('    python run_project.py')
run.font.name = 'Courier New'
run.font.size = Pt(10.5)
run.bold = True
doc.add_paragraph()

add_heading(doc, '4.3  Log Event Filters Applied', level=2)
add_body(doc, 'The following log message patterns are used to extract events from raw log data:')
add_table(doc,
    headers=['Event Type', 'Log Pattern', 'Action'],
    rows=[
        ['User Login',         "['Client Logged in'] UserName:",                        'Captured → Active Users Start'],
        ['User Logout',        "['UserLogOut'] UserName:",                               'Captured → Active Users End'],
        ['Single Ses. Start',  '[SOURCE : CONTROLLER. DESKTOP CONNECTED]',              'Captured → Single Session Start'],
        ['Single Ses. End',    '[SOURCE : HYDESK] ... session dismissal',               'Captured → Single Session End'],
        ['Multi Ses. Start',   "[SOURCE : SESSION HOST] ... Status changed to 'Connected'", 'Captured → Multi Session Start'],
        ['Multi Ses. End',     "[SOURCE : SESSION HOST] ... Status changed to 'LogOut'", 'Captured → Multi Session End'],
        ['User Disconnect',    "[SOURCE : SESSION HOST] ... Status changed to Disconnect", 'EXCLUDED — not treated as logout'],
    ]
)

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 5 — SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
add_heading(doc, '5. Summary', level=1)

p = doc.add_paragraph()
shade_paragraph(p, 'EBF0FA')
run = p.add_run(
    '  Random Forest Regressor was chosen as the final prediction model because it '
    'delivered a 96.52% improvement in Mean Absolute Error over the baseline model, '
    'while remaining robust, interpretable, and computationally efficient on structured '
    'tabular time-series data. It handles non-linear usage patterns, holiday flags, and '
    'weekend effects natively — making it the most practical and accurate choice for '
    'forecasting concurrent resource usage in this environment.'
)
run.font.size = Pt(11)
run.italic = True
doc.add_paragraph()

# ── Footer ─────────────────────────────────────────────────────────────────────
footer_section = doc.sections[0]
footer = footer_section.footer
footer_para = footer.paragraphs[0]
footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
footer_run = footer_para.add_run('Resource Usage Prediction Model — Technical Note  |  Confidential')
footer_run.font.size = Pt(8)
footer_run.font.color.rgb = RGBColor(150, 150, 150)

# ── Save ───────────────────────────────────────────────────────────────────────
output_path = 'Model_Selection_and_System_Requirements.docx'
doc.save(output_path)
print(f"Document saved: {output_path}")
