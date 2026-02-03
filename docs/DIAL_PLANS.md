# Dial Plans Feature Documentation

## Overview

The Dial Plans feature provides phone number transformation capabilities for SIP devices. It allows administrators to define regex-based rules that automatically transform dialed numbers before they are sent to the SIP server. This is useful for adding area codes, international prefixes, or normalizing phone number formats.

**Key Characteristics:**
- **Site-Based**: Each site can have one dial plan assigned (optional, nullable)
- **Rule-Based**: Each dial plan contains ordered transformation rules
- **First-Match**: Rules are applied in sequence order; first matching rule wins
- **Standard Syntax**: User-friendly regex format (`X`, `*`, `[]`, `$1`, `$2`)
- **Renderer-Agnostic**: Device renderers convert to device-specific format
- **Testable**: Built-in test function validates transformations

## Architecture

### Data Model

```
DialPlan (1) ─→ (Many) DialPlanRule
    ↓
Site.dial_plan (FK, nullable, SET_NULL)
    ↓
Device accesses via device.site.dial_plan.rules
```

**DialPlan Model:**
- `id` - Primary key
- `name` - Unique dial plan name
- `description` - Optional description
- `created_at` - Timestamp
- `updated_at` - Timestamp
- `rules` - Reverse relation to DialPlanRule
- `sites` - Reverse relation to Site (via related_name)

**DialPlanRule Model:**
- `id` - Primary key
- `dial_plan` - Foreign key to DialPlan
- `input_regex` - Pattern to match (standard format)
- `output_regex` - Replacement pattern (standard format)
- `sequence_order` - Integer ordering (0-based)
- Unique constraint: `(dial_plan, sequence_order)`

**Site Model Update:**
- `dial_plan` - ForeignKey to DialPlan (null=True, blank=True, on_delete=SET_NULL)

### Standard Regex Format

The dial plan system uses a **user-friendly regex syntax** that abstracts away Python regex complexity:

| Standard | Python Regex | Description | Example |
|----------|--------------|-------------|---------|
| `X` | `[0-9]` | Single digit (0-9) | `0X` matches `01`, `09` |
| `*` | `.+` | One or more characters | `0X*` matches `0288112233` |
| `[]` | `[]` | Literal brackets (pass-through) | `[123]` matches `[123]` |
| `[^]` | `[^]` | Literal brackets (pass-through) | `[^5]` matches `[^5]` |
| `()` | `()` | Capture group | `(0X*)` captures digits after 0 |
| `$1`, `$2` | `\1`, `\2` | Replacement references | `+61$1` replaces with +61 + captured group |

### Conversion Logic

The `StandardRegexConverter` class in `backend/core/dialplan_utils.py` handles conversion:

**Input Pattern Conversion:**
```python
def convert_input_pattern(pattern: str) -> tuple[str, Optional[str]]:
    """
    Converts user-friendly pattern to Python regex.
    
    Examples:
        "0X*"      → r"0[0-9].+"
        "(0X*)"    → r"(0[0-9].+)"
        "X*"       → r"[0-9].+"
    """
```

**Output Pattern Conversion:**
```python
def convert_output_pattern(pattern: str) -> tuple[str, Optional[str]]:
    """
    Converts $1, $2 to \1, \2 for Python re.sub().
    
    Examples:
        "+61$1"    → r"+61\1"
        "$1-$2"    → r"\1-\2"
    """
```

### Application Algorithm

The `apply_dial_plan()` function implements first-match logic:

```python
def apply_dial_plan(phone_number: str, rules: QuerySet[DialPlanRule]) -> tuple[str, Optional[int]]:
    """
    Apply dial plan rules to phone number.
    
    Algorithm:
    1. Iterate rules in sequence_order
    2. Convert input_regex to Python regex
    3. Try to match phone_number
    4. If match:
       a. Convert output_regex to Python replacement
       b. Apply transformation
       c. Return (transformed_number, sequence_order)
    5. If no match found, return (original_number, None)
    
    Returns:
        (transformed_number, matched_rule_index) or (original_number, None)
    """
```

## Backend Implementation

### Models (`backend/core/models.py`)

```python
class DialPlan(models.Model):
    """Container for phone number transformation rules."""
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class DialPlanRule(models.Model):
    """Individual transformation rule within a dial plan."""
    dial_plan = models.ForeignKey(DialPlan, on_delete=models.CASCADE, related_name='rules')
    input_regex = models.CharField(max_length=255)
    output_regex = models.CharField(max_length=255)
    sequence_order = models.IntegerField()
    
    class Meta:
        ordering = ['sequence_order']
        unique_together = [['dial_plan', 'sequence_order']]
    
    def __str__(self):
        return f"{self.dial_plan.name} Rule {self.sequence_order}"
```

### Utilities (`backend/core/dialplan_utils.py`)

Key functions:
- `StandardRegexConverter.convert_input_pattern(pattern)` - Converts X/*/() to Python regex
- `StandardRegexConverter.convert_output_pattern(pattern)` - Converts $1/$2 to \1/\2
- `validate_dial_plan_rule(input_regex, output_regex)` - Validates both patterns
- `apply_dial_plan(phone_number, rules)` - Applies rules and returns transformed number

### Serializers (`backend/core/serializers.py`)

**DialPlanRuleSerializer:**
- Fields: `id`, `input_regex`, `output_regex`, `sequence_order`
- Validation: Calls `validate_dial_plan_rule()` on both patterns

**DialPlanSerializer:**
- Fields: `id`, `name`, `description`, `rules` (nested), `rules_count`, `site_count`, `created_at`, `updated_at`
- Nested: `rules` is many=True with DialPlanRuleSerializer
- Create/Update: Handles nested rule creation with automatic sequence ordering

**SiteSerializer:**
- Added field: `dial_plan` (nullable FK)

### ViewSet (`backend/core/views.py`)

**DialPlanViewSet:**
- Permission: `IsAuthenticated` + `IsAdminOrReadOnly`
- Standard CRUD: list, retrieve, create, update, destroy
- Custom action: `test` (POST `/api/dial-plans/test/`)

**Delete Protection:**
- `destroy()` checks if dial plan is used by sites
- Returns HTTP 409 Conflict with count of sites using dial plan
- Prevents deletion if in use

**Test Action:**
```python
@action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
def test(self, request):
    """
    Test dial plan transformation.
    
    POST /api/dial-plans/test/
    Body: {
        "dial_plan_id": 1,
        "input_number": "0289185593"
    }
    
    Response: {
        "output": "+61289185593",
        "matched": true,
        "matched_rule_index": 0,
        "matched_rule_pattern": "0X*"
    }
    """
```

### URL Routes (`backend/phone_manager/urls.py`)

```python
router.register(r"dial-plans", core_views.DialPlanViewSet, basename="dialplan")
```

**Endpoints:**
- `GET /api/dial-plans/` - List all dial plans
- `POST /api/dial-plans/` - Create new dial plan
- `GET /api/dial-plans/{id}/` - Retrieve dial plan details
- `PATCH /api/dial-plans/{id}/` - Update dial plan
- `DELETE /api/dial-plans/{id}/` - Delete dial plan
- `POST /api/dial-plans/test/` - Test transformation

## Frontend Implementation

### API Service (`frontend/src/services/dialPlanService.js`)

```javascript
export const dialPlanService = {
  list() - Get all dial plans
  get(id) - Get specific dial plan
  create(data) - Create new dial plan
  update(id, data) - Update dial plan
  delete(id) - Delete dial plan
  test(dialPlanId, inputNumber) - Test transformation
};
```

### Dial Plans Page (`frontend/src/pages/DialPlansPage.vue`)

**Features:**
- Full CRUD operations (create, read, update, delete)
- Rules table with inline editing
- Sequence ordering (move up/down buttons)
- Test function with visual feedback
- Read-only mode support
- Comprehensive error handling

**UI Components:**

1. **Main Table:**
   - Columns: Name, Description, Rules Count, In Use (site count), Actions
   - Pagination: 20/50/100/All per page
   - Sort by name, description, rules count

2. **Create/Edit Dialog:**
   - Name input (required, unique)
   - Description textarea (optional)
   - Rules nested table with:
     - Sequence order with move up/down buttons
     - Input pattern field
     - Output pattern field
     - Delete rule button
   - Add Rule button
   - Test section with input box and result display

3. **Test Section:**
   - Input number field (only enabled after save)
   - Test button (calls API)
   - Result display:
     - Green banner: Match found with rule index and pattern
     - Orange banner: No match, original number returned

4. **Delete Confirmation:**
   - Shows item name
   - Error display if deletion fails (e.g., in use by sites)
   - Dialog stays open on error

**Read-Only Mode:**
- View button (eye icon) instead of Edit button
- All form fields disabled
- Save button hidden, only Close button visible
- Test function still available (readonly users can test)

### Sites Page Update (`frontend/src/pages/SitesPage.vue`)

**Changes:**
- Added `dial_plan` to form structure (nullable)
- Added `dialPlanOptions` computed property with "— None —" option
- Added `loadDialPlans()` function using dialPlanService
- Added dial plan dropdown in edit dialog (after Secondary SIP Server)
- Loads dial plans on mount

**UI:**
```vue
<q-select
  v-model="form.dial_plan"
  :options="dialPlanOptions"
  label="Dial Plan (optional)"
  dense
  outlined
  emit-value
  map-options
  clearable
  :disable="isReadOnly"
/>
```

### Router Update (`frontend/src/router/index.js`)

Added route:
```javascript
{ path: '/dial-plans', component: DialPlansPage, meta: { requiresAuth: true } }
```

### Navigation Update (`frontend/src/layouts/MainLayout.vue`)

Added menu item:
```vue
<q-route-tab to="/dial-plans" label="Dial Plans" icon="transform" />
```

Position: Between "SIP Servers" and "Sites"

## Usage Examples

### Example 1: Australian Local to International

**Scenario:** Convert local numbers (02XXXXXXXX) to international format (+61XXXXXXXXX)

**Rule Configuration:**
```
Input Pattern:  0X*
Output Pattern: +61$1
```

**Test Cases:**
- Input: `0289185593` → Output: `+61289185593`
- Input: `0398765432` → Output: `+61398765432`
- Input: `1300123456` → Output: `1300123456` (no match)

### Example 2: Multi-Rule Dial Plan

**Scenario:** Handle multiple number formats

**Rules (in sequence):**
1. Local to international: `0X*` → `+61$1`
2. Short codes unchanged: `1X*` → `$1`
3. International prefix: `00X*` → `+$1`

**Test Cases:**
- Input: `0289185593` → Output: `+61289185593` (Rule 1 matches)
- Input: `1300123456` → Output: `1300123456` (Rule 2 matches)
- Input: `0013035551234` → Output: `+13035551234` (Rule 3 matches)
- Input: `5551234` → Output: `5551234` (no match)

### Example 3: Area Code Addition

**Scenario:** Add area code to 7-digit local numbers

**Rule Configuration:**
```
Input Pattern:  XXXXXXX
Output Pattern: 02$1
```

**Test Cases:**
- Input: `8918559` → Output: `028918559`
- Input: `5551234` → Output: `025551234`
- Input: `0289185593` → Output: `0289185593` (no match, too many digits)

## Device Renderer Integration

### Accessing Dial Plans in Renderers

Device renderers access dial plans through the device's site relationship:

```python
def render(self, device: Device) -> str:
    """Generate device configuration."""
    
    # Access dial plan from site
    if device.site and device.site.dial_plan:
        dial_plan = device.site.dial_plan
        rules = dial_plan.rules.order_by('sequence_order')
        
        # Convert rules to device-specific format
        config = self._render_dial_plan_rules(rules)
    else:
        # No dial plan configured
        config = ""
    
    return config
```

### Device-Specific Format Conversion

**Important:** Renderers **convert** the standard format to device-specific syntax but **do not execute** transformations. The phone itself applies the dial plan rules.

**Example: Yealink Format**

Standard format → Yealink dialplan.xml format:

```python
def _render_dial_plan_rules(self, rules):
    """Convert standard format to Yealink dialplan.xml"""
    xml = '<dialplan>\n'
    for rule in rules:
        # Convert X → x, * → ., () → (), $1 → $1 (Yealink uses similar format)
        yealink_input = rule.input_regex.replace('X', 'x')
        yealink_output = rule.output_regex  # Yealink uses $1, $2
        xml += f'  <rule input="{yealink_input}" output="{yealink_output}"/>\n'
    xml += '</dialplan>\n'
    return xml
```

**Example: Grandstream Format**

Standard format → Grandstream P-values:

```python
def _render_dial_plan_rules(self, rules):
    """Convert standard format to Grandstream P-value format"""
    config = ""
    for idx, rule in enumerate(rules):
        p_num = 200 + idx  # P200, P201, P202, etc.
        # Grandstream uses { } for replace, x for digit
        gs_input = rule.input_regex.replace('X', 'x').replace('*', '.')
        gs_output = rule.output_regex.replace('$1', '{$1}').replace('$2', '{$2}')
        config += f'P{p_num} = {gs_input},{gs_output}\n'
    return config
```

## Testing

### Backend Unit Tests

Key test cases for `dialplan_utils.py`:

```python
def test_standard_regex_conversion():
    # X → [0-9]
    assert convert_input_pattern("X") == (r"[0-9]", None)
    
    # * → .+
    assert convert_input_pattern("*") == (r".+", None)
    
    # Combined
    assert convert_input_pattern("0X*") == (r"0[0-9].+", None)

def test_apply_dial_plan():
    # First match wins
    rules = [
        DialPlanRule(input_regex="0X*", output_regex="+61$1", sequence_order=0),
        DialPlanRule(input_regex="X*", output_regex="02$1", sequence_order=1)
    ]
    result, matched = apply_dial_plan("0289185593", rules)
    assert result == "+61289185593"
    assert matched == 0  # First rule matched
```

### Frontend Testing

**Manual Test Procedure:**

1. **Create Dial Plan:**
   - Navigate to Dial Plans page
   - Click "Add" button
   - Enter name: "AU International"
   - Add rule: `0X*` → `+61$1`
   - Click "Save"

2. **Test Transformation:**
   - Open edit dialog for created dial plan
   - Enter test input: `0289185593`
   - Click "Test" button
   - Verify output: `+61289185593`
   - Verify matched rule index: 0

3. **Assign to Site:**
   - Navigate to Sites page
   - Edit a site
   - Select "AU International" from Dial Plan dropdown
   - Save site

4. **Verify Delete Protection:**
   - Navigate to Dial Plans page
   - Try to delete "AU International"
   - Verify error: "Cannot delete this dial plan as it is currently used by 1 site(s)"

## Permissions & Security

### Role-Based Access Control

| Role | List/View | Test | Create | Edit | Delete |
|------|-----------|------|--------|------|--------|
| **Admin** | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Read Only** | ✓ | ✓ | ✗ | ✗ | ✗ |

**Implementation:**
- Backend: `IsAdminOrReadOnly` permission class
- Frontend: `isReadOnly` computed property hides action buttons
- Test function available to all authenticated users

### Validation

**Backend Validation:**
- Dial plan name must be unique
- Input/output patterns validated by `validate_dial_plan_rule()`
- Regex patterns must compile successfully
- Foreign key constraint protection on delete

**Frontend Validation:**
- Name required (non-empty)
- Input pattern required for each rule
- Output pattern required for each rule
- Test requires saved dial plan ID + input number

## Migration

**Migration File:** `backend/core/migrations/0008_dialplan_site_dial_plan_dialplanrule.py`

**Changes:**
1. Create DialPlan table
2. Create DialPlanRule table with FK to DialPlan
3. Add dial_plan FK to Site table (nullable, SET_NULL)

**Rollback Safety:**
- SET_NULL on delete ensures sites remain valid if dial plan deleted
- Nullable field means no data migration required for existing sites

## Future Enhancements

### Planned Features

1. **Import/Export:**
   - Export dial plans as JSON/CSV
   - Import dial plans from file
   - Template library with common dial plans

2. **Advanced Rules:**
   - Conditional rules (time-based, caller ID-based)
   - Blacklist/whitelist patterns
   - Call cost calculation based on patterns

3. **Analytics:**
   - Track which rules are matched most frequently
   - Show transformation statistics
   - Alert on never-matched rules

4. **Device-Specific Rendering:**
   - Auto-detect device capabilities
   - Warn if dial plan exceeds device limits
   - Preview device-specific format

5. **Testing Improvements:**
   - Bulk test with CSV input
   - Test against all rules (show all matches, not just first)
   - Regex validation hints in UI

## Troubleshooting

### Common Issues

**Issue:** Dial plan not applying to device
- **Check:** Device must be assigned to a site with dial_plan set
- **Check:** Device renderer must implement dial plan conversion
- **Check:** Phone firmware supports dial plans

**Issue:** Test function shows no match
- **Verify:** Input pattern uses correct syntax (X, *, not x or [0-9])
- **Verify:** Pattern compiles without errors
- **Verify:** Input number actually matches pattern

**Issue:** Cannot delete dial plan
- **Cause:** Dial plan is assigned to one or more sites
- **Solution:** Remove dial plan from sites first, or assign different dial plan

**Issue:** Rules not executing in order
- **Check:** sequence_order field is correct (0, 1, 2, ...)
- **Check:** Move up/down buttons update sequence correctly
- **Remember:** First match wins, later rules not evaluated

### Logging

**Backend Logging:**
```python
logger.info(f"Created dial plan: {dial_plan.name}")
logger.info(f"Tested dial plan '{dial_plan.name}' on '{input_number}' -> '{output}'")
logger.info(f"Deleted dial plan: {instance.name}")
```

**Location:** `var/logs/backend.log`

**Frontend Logging:**
```javascript
console.error('Error loading dial plans:', error);
```

## References

- [Python re module documentation](https://docs.python.org/3/library/re.html)
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture overview
- [FRONTEND_GUIDELINES.md](FRONTEND_GUIDELINES.md) - UI patterns and validation
- [API.md](API.md) - REST API reference

---

**Copyright (c) 2026 Slinky Software**
**License:** GPL-3.0-or-later
