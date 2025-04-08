#include "FilterDialog.h"
#include <QVBoxLayout>

FilterDialog::FilterDialog(QWidget* parent) : QDialog(parent) {
    QVBoxLayout* mainLayout = new QVBoxLayout(this);
    QFormLayout* formLayout = new QFormLayout();

    // Формат
    formatCombo = new QComboBox(this);
    formatCombo->addItems({"Online", "Offline"});
    formLayout->addRow("Формат:", formatCombo);

    // Город
    cityEdit = new QLineEdit(this);
    formLayout->addRow("Город:", cityEdit);

    // Теги
    tagsEdit = new QLineEdit(this);
    tagsEdit->setPlaceholderText("через запятую");
    formLayout->addRow("Теги:", tagsEdit);

    // Координаты
    /*
    latSpin = new QDoubleSpinBox(this);
    latSpin->setRange(-90.0, 90.0);
    latSpin->setDecimals(6);
    formLayout->addRow("Широта:", latSpin);

    lonSpin = new QDoubleSpinBox(this);
    lonSpin->setRange(-180.0, 180.0);
    lonSpin->setDecimals(6);
    formLayout->addRow("Долгота:", lonSpin);

    // Радиус
    radiusSpin = new QDoubleSpinBox(this);
    radiusSpin->setRange(0.0, 10000.0);
    radiusSpin->setSuffix(" км");
    formLayout->addRow("Радиус поиска:", radiusSpin);
    */

    mainLayout->addLayout(formLayout);

    // Кнопки
    buttonBox = new QDialogButtonBox(
        QDialogButtonBox::Ok | QDialogButtonBox::Cancel,
        this
        );
    mainLayout->addWidget(buttonBox);

    connect(buttonBox, &QDialogButtonBox::accepted, this, &QDialog::accept);
    connect(buttonBox, &QDialogButtonBox::rejected, this, &QDialog::reject);
}
