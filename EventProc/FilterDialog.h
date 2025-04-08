#pragma once
#include <QDialog>
#include <QComboBox>
#include <QDialogButtonBox>
#include <QDoubleSpinBox>
#include <QLineEdit>
#include <QFormLayout>

class FilterDialog : public QDialog {
    Q_OBJECT
public:
    explicit FilterDialog(QWidget* parent = nullptr);

    // Элементы управления
    QComboBox* formatCombo;
    QLineEdit* cityEdit;
    QLineEdit* tagsEdit;
    //QDoubleSpinBox* latSpin;
    //QDoubleSpinBox* lonSpin;
    //QDoubleSpinBox* radiusSpin;

private:
    QDialogButtonBox* buttonBox;
};
