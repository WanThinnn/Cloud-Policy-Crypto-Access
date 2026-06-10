// ========== POLICY BUILDER LOGIC ==========
// Shared logic for Policy Builder UI
let AVAILABLE_ATTRIBUTES = [];
let policyBuilderAttributesLoaded = false;
let elementCounter = 0;
let isAdvancedMode = false;

const OPERATORS = [
    { key: '==', label: 'equals' },
    { key: 'in', label: 'in list' },
];

async function loadPolicyBuilderAttributes() {
    if (policyBuilderAttributesLoaded && AVAILABLE_ATTRIBUTES.length > 0) {
        return AVAILABLE_ATTRIBUTES;
    }
    try {
        const response = await fetch('/api/admin/policy-builder-attributes/', { 
            headers: { 'X-CSRFToken': getCookie('csrftoken') } 
        });
        if (response.ok) {
            AVAILABLE_ATTRIBUTES = await response.json();
            policyBuilderAttributesLoaded = true;
        } else {
            AVAILABLE_ATTRIBUTES = [];
        }
    } catch (error) {
        AVAILABLE_ATTRIBUTES = [];
    }
    return AVAILABLE_ATTRIBUTES;
}

function createGroupHTML(groupId, isRoot = false) {
    return `
        <div class="condition-group ${isRoot ? 'border border-blue-300 rounded p-3 bg-blue-50/50 dark:bg-blue-900/10' : 'border-l-4 border-blue-400 pl-3 py-2 ml-4 mt-2 bg-gray-50 dark:bg-gray-800/50 rounded-r'}" data-group-id="${groupId}">
            <div class="group-header flex items-center mb-2">
                <span class="text-sm font-medium text-gray-700 dark:text-gray-300 mr-2">Match</span>
                <select class="group-connector-select bg-white dark:bg-gray-700 dark:text-white border border-gray-300 dark:border-gray-600 rounded px-2 py-1 text-sm font-bold text-blue-700" onchange="updatePreview()">
                    <option value="and">ALL (AND)</option>
                    <option value="or">ANY (OR)</option>
                </select>
                <span class="text-sm font-medium text-gray-700 dark:text-gray-300 ml-2">of the following:</span>
                ${!isRoot ? `
                    <button type="button" class="remove-group-btn ml-auto text-red-500 hover:text-red-700" onclick="this.closest('.condition-group').remove(); updatePreview();">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                    </button>
                ` : ''}
            </div>
            <div class="group-children space-y-2">
                <!-- Rules and subgroups go here -->
            </div>
            <div class="group-actions mt-2 flex gap-2">
                <button type="button" class="text-xs px-2 py-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-blue-600 hover:bg-blue-50" onclick="addRuleToGroup(${groupId})">
                    + Add Rule
                </button>
                <button type="button" class="text-xs px-2 py-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-purple-600 hover:bg-purple-50" onclick="addGroupToGroup(${groupId})">
                    + Add Group
                </button>
            </div>
        </div>
    `;
}

function createRuleHTML(ruleId) {
    const attrOptions = AVAILABLE_ATTRIBUTES.map(a => `<option value="${a.key}">${a.label}</option>`).join('');
    const opOptions = OPERATORS.map(o => `<option value="${o.key}">${o.label}</option>`).join('');

    return `
        <div class="condition-rule flex items-center gap-2 p-2 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700" data-rule-id="${ruleId}">
            <select class="attr-select bg-white dark:bg-gray-700 dark:text-white border border-gray-300 dark:border-gray-600 rounded px-2 py-1 text-sm" onchange="updateValueSelector(${ruleId})">
                ${attrOptions}
            </select>
            <select class="op-select bg-white dark:bg-gray-700 dark:text-white border border-gray-300 dark:border-gray-600 rounded px-2 py-1 text-sm" onchange="updateValueSelector(${ruleId})">
                ${opOptions}
            </select>
            <div class="value-container flex-1" data-rule-id="${ruleId}"></div>
            <button type="button" class="remove-rule-btn text-red-500 hover:text-red-700" onclick="this.closest('.condition-rule').remove(); updatePreview();">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
        </div>
    `;
}

window.addRuleToGroup = function(groupId, ruleData = null) {
    const group = document.querySelector(`.condition-group[data-group-id="${groupId}"] > .group-children`);
    const ruleId = ++elementCounter;
    group.insertAdjacentHTML('beforeend', createRuleHTML(ruleId));
    
    if (ruleData) {
        const rule = document.querySelector(`.condition-rule[data-rule-id="${ruleId}"]`);
        rule.querySelector('.attr-select').value = ruleData.attr;
        rule.querySelector('.op-select').value = ruleData.op;
    }
    updateValueSelector(ruleId, ruleData ? ruleData.value : null);
};

window.addGroupToGroup = function(groupId, connector = 'and') {
    const group = document.querySelector(`.condition-group[data-group-id="${groupId}"] > .group-children`);
    const newGroupId = ++elementCounter;
    group.insertAdjacentHTML('beforeend', createGroupHTML(newGroupId, false));
    
    const newGroup = document.querySelector(`.condition-group[data-group-id="${newGroupId}"]`);
    newGroup.querySelector('.group-connector-select').value = connector;
    
    updatePreview();
    return newGroupId;
};

window.updateValueSelector = function(ruleId, initialValue = null) {
    const rule = document.querySelector(`.condition-rule[data-rule-id="${ruleId}"]`);
    if (!rule) return;
    const attrSelect = rule.querySelector('.attr-select');
    const opSelect = rule.querySelector('.op-select');
    const valueContainer = rule.querySelector('.value-container');
    
    const selectedAttr = AVAILABLE_ATTRIBUTES.find(a => a.key === attrSelect.value);
    const isMultiSelect = opSelect.value === 'in' || opSelect.value === 'not in';
    const attrValues = selectedAttr?.values || [];

    if (isMultiSelect) {
        valueContainer.innerHTML = `
            <div class="flex flex-wrap gap-1">
                ${attrValues.map(v => `
                    <label class="inline-flex items-center bg-gray-100 dark:bg-gray-700 rounded px-2 py-1 text-xs">
                        <input type="checkbox" class="value-checkbox mr-1" value="${v}" onchange="updatePreview()">
                        ${v}
                    </label>
                `).join('')}
            </div>
        `;
        if (initialValue && Array.isArray(initialValue)) {
            rule.querySelectorAll('.value-checkbox').forEach(cb => {
                cb.checked = initialValue.includes(cb.value);
            });
        }
    } else {
        valueContainer.innerHTML = `
            <select class="value-select bg-white dark:bg-gray-700 dark:text-white border border-gray-300 dark:border-gray-600 rounded px-2 py-1 text-sm" onchange="updatePreview()">
                ${attrValues.map(v => `<option value="${v}">${v}</option>`).join('')}
            </select>
        `;
        if (initialValue) {
            rule.querySelector('.value-select').value = initialValue;
        }
    }
    updatePreview();
}

function buildConditionFromGroup(groupEl) {
    const children = Array.from(groupEl.querySelector('.group-children').children);
    if (children.length === 0) return '';
    
    const connector = groupEl.querySelector('.group-connector-select').value;
    const parts = [];
    
    children.forEach(child => {
        if (child.classList.contains('condition-group')) {
            const subCond = buildConditionFromGroup(child);
            if (subCond) parts.push(`(${subCond})`);
        } else if (child.classList.contains('condition-rule')) {
            const attr = child.querySelector('.attr-select').value;
            const op = child.querySelector('.op-select').value;
            let value;
            if (op === 'in' || op === 'not in') {
                const checkboxes = child.querySelectorAll('.value-checkbox:checked');
                const values = Array.from(checkboxes).map(cb => `'${cb.value}'`);
                if (values.length > 0) {
                    value = `[${values.join(', ')}]`;
                    parts.push(`r.sub.${attr} ${op} ${value}`);
                }
            } else {
                const select = child.querySelector('.value-select');
                if (select) {
                    parts.push(`r.sub.${attr} ${op} '${select.value}'`);
                }
            }
        }
    });
    
    return parts.join(` ${connector} `);
}

function buildConditionFromRules() {
    const rootGroup = document.querySelector('#query-builder-root > .condition-group');
    if (!rootGroup) return '';
    return buildConditionFromGroup(rootGroup);
}

window.updatePreview = function() {
    const preview = document.getElementById('condition-preview');
    if(!preview) return;
    const condition = isAdvancedMode 
        ? document.getElementById('subject_condition_input').value
        : buildConditionFromRules();
    
    if (condition) {
        preview.textContent = condition;
        preview.classList.remove('text-gray-400');
        preview.classList.add('text-green-700');
    } else {
        preview.textContent = '(No conditions yet)';
        preview.classList.remove('text-green-700');
        preview.classList.add('text-gray-400');
    }
    
    const finalInput = document.getElementById('subject_condition_final');
    if(finalInput) {
        finalInput.value = condition;
    }
};

window.toggleAdvancedMode = function() {
    isAdvancedMode = !isAdvancedMode;
    const simpleMode = document.getElementById('simple-mode');
    const advancedMode = document.getElementById('advanced-mode');
    const toggleBtn = document.getElementById('toggle-advanced');

    if (isAdvancedMode) {
        document.getElementById('subject_condition_input').value = buildConditionFromRules();
        simpleMode.classList.add('hidden');
        advancedMode.classList.remove('hidden');
        toggleBtn.textContent = 'Simple mode';
    } else {
        // Need to re-parse from input to visual builder if switching back
        parseConditionToRules(document.getElementById('subject_condition_input').value);
        simpleMode.classList.remove('hidden');
        advancedMode.classList.add('hidden');
        toggleBtn.textContent = 'Advanced mode';
    }
    updatePreview();
};

function initRootGroup() {
    const root = document.getElementById('query-builder-root');
    if(root) {
        root.innerHTML = createGroupHTML(0, true);
    }
}

async function parseConditionToRules(condition) {
    const root = document.getElementById('query-builder-root');
    if(!root) return;
    root.innerHTML = '';
    elementCounter = 0;
    initRootGroup();

    if (!condition) {
        addRuleToGroup(0);
        return;
    }

    try {
        const response = await fetch('/api/admin/policies/parse_ast/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/json' },
            body: JSON.stringify({ condition: condition })
        });
        const data = await response.json();
        
        if (data.tree) {
            // Clear root
            document.getElementById('query-builder-root').innerHTML = '';
            buildUIFromJson(data.tree, null);
        } else {
            addRuleToGroup(0);
        }
    } catch (error) {
        console.error("Failed to parse AST from server:", error);
        isAdvancedMode = true;
        document.getElementById('simple-mode').classList.add('hidden');
        document.getElementById('advanced-mode').classList.remove('hidden');
        document.getElementById('toggle-advanced').textContent = 'Simple mode';
        document.getElementById('subject_condition_input').value = condition;
    }
    updatePreview();
}

function buildUIFromJson(node, parentGroupId) {
    if (!node) return;
    
    if (node.type === 'group') {
        let groupId;
        if (parentGroupId === null) {
            // It's root
            groupId = 0;
            document.getElementById('query-builder-root').innerHTML = createGroupHTML(groupId, true);
        } else {
            groupId = addGroupToGroup(parentGroupId, node.connector);
        }
        
        const groupEl = document.querySelector(`.condition-group[data-group-id="${groupId}"]`);
        if (groupEl) {
            groupEl.querySelector('.group-connector-select').value = node.connector;
        }
        
        if (node.children) {
            node.children.forEach(child => buildUIFromJson(child, groupId));
        }
    } else if (node.type === 'rule' && parentGroupId !== null) {
        addRuleToGroup(parentGroupId, node);
    }
}

// Bind basic events safely
document.addEventListener('DOMContentLoaded', () => {
    const outerAddRuleBtn = document.getElementById('add-rule-btn');
    if (outerAddRuleBtn) {
        outerAddRuleBtn.addEventListener('click', () => {
            addRuleToGroup(0);
        });
    }
    
    const toggleAdvBtn = document.getElementById('toggle-advanced');
    if(toggleAdvBtn) {
        toggleAdvBtn.addEventListener('click', toggleAdvancedMode);
    }
    
    const inputCond = document.getElementById('subject_condition_input');
    if(inputCond) {
        inputCond.addEventListener('input', updatePreview);
    }
});

// Initialization hook
window.initPolicyBuilder = async function(existingCondition = "") {
    await loadPolicyBuilderAttributes();
    if (AVAILABLE_ATTRIBUTES.length === 0) {
        isAdvancedMode = true;
    } else {
        isAdvancedMode = false;
    }
    
    if (isAdvancedMode) {
        document.getElementById('simple-mode').classList.add('hidden');
        document.getElementById('advanced-mode').classList.remove('hidden');
        document.getElementById('toggle-advanced').textContent = 'Simple mode';
    } else {
        document.getElementById('simple-mode').classList.remove('hidden');
        document.getElementById('advanced-mode').classList.add('hidden');
        document.getElementById('toggle-advanced').textContent = 'Advanced mode';
    }
    
    if (existingCondition) {
        await parseConditionToRules(existingCondition);
        document.getElementById('subject_condition_input').value = existingCondition;
    } else {
        const root = document.getElementById('query-builder-root');
        if(root) root.innerHTML = '';
        elementCounter = 0;
        if (!isAdvancedMode) {
            initRootGroup();
            addRuleToGroup(0);
        }
    }
    updatePreview();
};
