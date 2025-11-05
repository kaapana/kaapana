# Workflow Form Validation Guide

## Overview
The WorkflowRunForm component now includes comprehensive native Vuetify validation without relying on external libraries like vjsf.

## Validation Features

### 1. **Required Field Indicators**
- Required fields are marked with an asterisk (*) in the label
- Example: "Epochs *", "Learning Rate *"

### 2. **Field-Specific Validation**

#### Integer Fields
- **Type validation**: Must be a valid integer
- **Range validation**: 
  - Minimum value check (e.g., "Must be at least 1")
  - Maximum value check (e.g., "Must be at most 1000")
- **Hint displays**: Shows range information (e.g., "Range: 1 - 1000")

#### Float Fields
- **Type validation**: Must be a valid number
- **Range validation**:
  - Minimum value check (e.g., "Must be at least 0.0001")
  - Maximum value check (e.g., "Must be at most 1.0")
- **Hint displays**: Shows range information (e.g., "Range: 0.0001 - 1.0")

#### String Fields
- **Required validation**: Checks for non-empty values
- **Regex pattern validation**: 
  - Dataset paths: Must match `^/(data|datasets)/[a-zA-Z0-9_/-]+$`
  - Dataset names: Must match `^[a-zA-Z0-9_-]{3,50}$`
  - Email addresses: Must match valid email format
- **Custom error messages**: Shows pattern requirements

#### List Fields (Select/Multi-select)
- **Required validation**: For single-select, must have a value
- **Multi-select validation**: Must have at least one item selected
- **Visual feedback**: Shows chips for multi-select items

#### Boolean Fields
- **No validation needed**: Switches have valid states by default
- **Optional required indicator**: Shows asterisk if marked as required

### 3. **Visual Feedback**

#### Real-time Validation
- Validation occurs as users type or change values
- Error messages appear immediately below fields
- Invalid fields show red error state

#### Error States
- **Red border**: Invalid fields highlighted in red
- **Shake animation**: Fields shake when validation fails
- **Error messages**: Clear, specific error text
- **Disabled submit**: "Run Workflow" button disabled when form invalid

#### Help Tooltips
- **Info icon**: Displayed for fields with help text
- **Hover interaction**: Shows detailed help on hover
- **Positioned**: Appears above the icon to avoid overlapping content

### 4. **Form-Level Validation**
- Form tracks overall validity state
- Submit button disabled when:
  - Form is invalid
  - Form is loading
- Validation check runs before submission
- Prevents submission if any field is invalid

## Mock Data Examples

### Integer with Validation
```python
WorkflowParameter(
    env_variable_name="EPOCHS",
    ui_form=IntegerUIForm(
        type="int",
        title="Epochs",
        description="Specify the number of training epochs.",
        help="How many epochs of nnUnet model training should be run?",
        required=True,
        default=10,
        minimum=1,
        maximum=1000,
    ),
)
```

### Float with Validation
```python
WorkflowParameter(
    env_variable_name="LR",
    ui_form=FloatUIForm(
        type="float",
        title="Learning Rate",
        description="Initial learning rate.",
        help="Learning rate for model training.",
        default=0.001,
        minimum=0.0001,
        maximum=1.0,
        required=True,
    ),
)
```

### String with Regex Validation
```python
WorkflowParameter(
    env_variable_name="DATASET_PATH",
    ui_form=StringUIForm(
        type="str",
        title="Dataset Path",
        description="Path to the dataset directory.",
        help="Must be an absolute path starting with /data/ or /datasets/",
        default="/data/input",
        regex_pattern="^/(data|datasets)/[a-zA-Z0-9_/-]+$",
        required=True,
    ),
)
```

### Multi-select with Required Validation
```python
WorkflowParameter(
    env_variable_name="ORGANS",
    ui_form=ListUIForm(
        type="list",
        title="Included Organs",
        description="Choose organs to include.",
        help="Select one or more organs. At least one must be selected.",
        options=["lung", "liver", "spleen", "kidney"],
        multiselectable=True,
        required=True,
        default=["liver"],
    ),
)
```

## Testing Validation

### How to Test
1. Open the workflow form dialog
2. Try invalid values:
   - **Integers**: Enter text, negative numbers, or out-of-range values
   - **Floats**: Enter invalid decimals or out-of-range values
   - **Strings**: Enter values that don't match the regex pattern
   - **Required fields**: Clear required fields and try to submit
3. Observe validation feedback:
   - Error messages appear
   - Fields turn red
   - Submit button becomes disabled
4. Fix the errors and verify:
   - Error messages disappear
   - Fields return to normal state
   - Submit button becomes enabled

### Expected Behavior
- ✅ Valid form allows submission
- ❌ Invalid form disables submission
- 🔴 Error fields show clear messages
- ℹ️ Help tooltips provide guidance
- ⚠️ Required fields marked with asterisk

## Implementation Benefits

1. **No External Dependencies**: Removed vjsf library
2. **Native Vuetify**: Uses built-in form validation
3. **Type-Safe**: Full TypeScript support
4. **Customizable**: Easy to add new validation rules
5. **Accessible**: Proper ARIA labels and error associations
6. **Performance**: Lightweight and efficient
7. **Maintainable**: Clear, readable code structure

## Future Enhancements

Potential improvements:
- Async validation for dataset/entity fields
- Custom validation for complex business rules
- Field dependencies (enable/disable based on other fields)
- Validation summary showing all errors at once
- Save draft functionality for partial forms
