[CmdletBinding()]
param(
    [string]$DocumentPath,
    [string]$PlanPath
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
if ([string]::IsNullOrWhiteSpace($DocumentPath)) {
    $DocumentPath = Join-Path $repoRoot "docs/governance/EXTERNAL_REQUIREMENTS_MATRIX.md"
}
if ([string]::IsNullOrWhiteSpace($PlanPath)) {
    $PlanPath = Join-Path $repoRoot "docs/PLAN_MAESTRO_FINALIZACION_ZERO_MERMA.md"
}

$resolvedDocument = (Resolve-Path -LiteralPath $DocumentPath).Path
$resolvedPlan = (Resolve-Path -LiteralPath $PlanPath).Path
$decisionsPath = Join-Path $repoRoot "docs/DECISIONES_ZERO_MERMA.md"
$failures = [System.Collections.Generic.List[string]]::new()

function Add-Failure {
    param([string]$Message)
    $failures.Add($Message)
}

function Test-HasValue {
    param($Value)
    if ($null -eq $Value) { return $false }
    if ($Value -is [string]) { return -not [string]::IsNullOrWhiteSpace($Value) }
    if ($Value -is [System.Collections.IEnumerable]) { return @($Value).Count -gt 0 }
    return $true
}

function Get-JsonBlock {
    param(
        [string]$Text,
        [string]$Name
    )

    $escapedName = [regex]::Escape($Name)
    $pattern = '(?s)<!-- ZM-FIN-007:{0}:BEGIN -->\s*```json\s*(.*?)\s*```\s*<!-- ZM-FIN-007:{0}:END -->' -f $escapedName
    $matches = [regex]::Matches($Text, $pattern)
    if ($matches.Count -ne 1) {
        throw "Expected exactly one JSON block for $Name, found $($matches.Count)."
    }

    try {
        return @($matches[0].Groups[1].Value | ConvertFrom-Json -Depth 30)
    }
    catch {
        throw "Invalid JSON in block ${Name}: $($_.Exception.Message)"
    }
}

function Test-UniqueIds {
    param(
        [object[]]$Items,
        [string]$PropertyName,
        [string]$Label
    )

    $ids = @($Items | ForEach-Object { $_.$PropertyName })
    $duplicates = @($ids | Group-Object | Where-Object Count -gt 1 | ForEach-Object Name)
    if ($duplicates.Count -gt 0) {
        Add-Failure "$Label IDs are not unique: $($duplicates -join ', ')."
    }
}

function Get-HardTaskDependencies {
    param([string]$DependencyText)

    # The first clause of field 8 is the hard dependency list. Text after a
    # semicolon or full stop documents external prerequisites or explicit
    # non-dependencies and must not become a graph edge.
    $hardClause = ($DependencyText -split ';', 2)[0]
    $hardClause = ($hardClause -split '\.\s+', 2)[0]
    $references = [System.Collections.Generic.List[string]]::new()

    foreach ($match in [regex]::Matches($hardClause, 'ZM-FIN-(?<start>\d{3})(?:(?<range>[\u2013-])(?<end>\d{3})|/(?<alternate>\d{3}))?')) {
        $start = [int]$match.Groups['start'].Value
        if ($match.Groups['end'].Success) {
            $end = [int]$match.Groups['end'].Value
            if ($end -lt $start) {
                throw "Descending task dependency range is invalid: $($match.Value)."
            }
            foreach ($number in $start..$end) {
                [void]$references.Add(('ZM-FIN-{0:D3}' -f $number))
            }
        }
        elseif ($match.Groups['alternate'].Success) {
            [void]$references.Add(('ZM-FIN-{0:D3}' -f $start))
            [void]$references.Add(('ZM-FIN-{0:D3}' -f [int]$match.Groups['alternate'].Value))
        }
        else {
            [void]$references.Add(('ZM-FIN-{0:D3}' -f $start))
        }
    }

    return @($references | Sort-Object -Unique)
}

function Find-DependencyCycle {
    param([hashtable]$Dependencies)

    $state = @{}
    foreach ($taskId in $Dependencies.Keys) {
        $state[$taskId] = 0
    }
    $path = [System.Collections.Generic.List[string]]::new()

    function Visit-DependencyNode {
        param([string]$TaskId)

        $state[$TaskId] = 1
        [void]$path.Add($TaskId)
        foreach ($dependency in @($Dependencies[$TaskId] | Sort-Object)) {
            if (-not $state.ContainsKey($dependency)) {
                continue
            }
            if ($state[$dependency] -eq 1) {
                $cycleStart = $path.IndexOf($dependency)
                $cycle = @($path.GetRange($cycleStart, $path.Count - $cycleStart))
                $cycle += $dependency
                return $cycle
            }
            if ($state[$dependency] -eq 0) {
                $cycle = @(Visit-DependencyNode -TaskId $dependency)
                if ($cycle.Count -gt 0) {
                    return $cycle
                }
            }
        }

        $path.RemoveAt($path.Count - 1)
        $state[$TaskId] = 2
        return @()
    }

    foreach ($taskId in @($Dependencies.Keys | Sort-Object)) {
        if ($state[$taskId] -eq 0) {
            $cycle = @(Visit-DependencyNode -TaskId $taskId)
            if ($cycle.Count -gt 0) {
                return $cycle
            }
        }
    }

    return @()
}

$bytes = [System.IO.File]::ReadAllBytes($resolvedDocument)
if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    Add-Failure "Document must not contain a UTF-8 BOM."
}

try {
    $strictUtf8 = [System.Text.UTF8Encoding]::new($false, $true)
    $document = $strictUtf8.GetString($bytes)
}
catch {
    Add-Failure "Document is not valid UTF-8: $($_.Exception.Message)"
    $document = [System.Text.Encoding]::UTF8.GetString($bytes)
}

if ($document.Contains("`r")) {
    Add-Failure "Document must use LF line endings only."
}
if (-not $document.EndsWith("`n")) {
    Add-Failure "Document must end with LF."
}

$requiredHeadings = @(
    "## Purpose and authority",
    "## Canonical sources and decision boundaries",
    "## Current data inventory",
    "## Current and planned document inventory",
    "## Canonical requirement matrix",
    "## Retention categories",
    "## BBVA and PCI production gate",
    "## Privacy and ARCO boundary",
    "## Third-party and multi-tenant boundary",
    "## External validations",
    "## Accepted out-of-scope items",
    "## Plan gaps",
    "## Required test catalog",
    "## Gate and task summary",
    "## ZM-FIN-007 closure assessment"
)
foreach ($heading in $requiredHeadings) {
    if (-not $document.Contains($heading)) {
        Add-Failure "Missing required section: $heading."
    }
}

$fenceCount = ([regex]::Matches($document, '(?m)^```')).Count
if (($fenceCount % 2) -ne 0) {
    Add-Failure "Markdown fences are unbalanced."
}

$requirements = Get-JsonBlock -Text $document -Name "REQUIREMENTS"
$tests = Get-JsonBlock -Text $document -Name "TESTS"
$externalValidations = Get-JsonBlock -Text $document -Name "EXTERNAL-VALIDATIONS"
$outOfScope = Get-JsonBlock -Text $document -Name "OUT-OF-SCOPE"
$planGaps = @(Get-JsonBlock -Text $document -Name "PLAN-GAPS" | Where-Object { $null -ne $_ })

$plan = Get-Content -Raw -LiteralPath $resolvedPlan
$decisions = Get-Content -Raw -LiteralPath $decisionsPath
$planTaskIdList = @([regex]::Matches($plan, '(?m)^###\s+(ZM-FIN-\d{3})\b') | ForEach-Object { $_.Groups[1].Value })
$planTaskIds = [System.Collections.Generic.HashSet[string]]::new([string[]]$planTaskIdList)
$decisionIds = [System.Collections.Generic.HashSet[string]]::new([string[]]([regex]::Matches($decisions, '\bDEC-\d{2}\b') | ForEach-Object Value | Sort-Object -Unique))
$validGates = [System.Collections.Generic.HashSet[string]]::new([string[]](0..9 | ForEach-Object { "G$_" }))

Test-UniqueIds -Items @($planTaskIdList | ForEach-Object { [pscustomobject]@{ task_id = $_ } }) -PropertyName "task_id" -Label "Plan task"
if ($planTaskIds.Count -ne 130) {
    Add-Failure "Expected 130 Plan task IDs, found $($planTaskIds.Count)."
}
if ($decisionIds.Count -ne 20) {
    Add-Failure "Expected 20 canonical decision IDs, found $($decisionIds.Count)."
}

$expectedPlanTaskIds = @(1..130 | ForEach-Object { "ZM-FIN-{0:D3}" -f $_ })
$missingPlanTaskIds = @($expectedPlanTaskIds | Where-Object { -not $planTaskIds.Contains($_) })
$unexpectedPlanTaskIds = @($planTaskIds | Where-Object { $_ -notin $expectedPlanTaskIds })
if ($missingPlanTaskIds.Count -gt 0) {
    Add-Failure "Missing canonical Plan task IDs: $($missingPlanTaskIds -join ', ')."
}
if ($unexpectedPlanTaskIds.Count -gt 0) {
    Add-Failure "Unexpected Plan task IDs: $($unexpectedPlanTaskIds -join ', ')."
}

$taskDependencies = @{}
$dependencyReferencesValid = $true
$selfDependencyCount = 0
$taskBlocks = [regex]::Matches($plan, '(?ms)^###\s+(?<id>ZM-FIN-\d{3})\b.*?(?=^###\s+ZM-FIN-\d{3}\b|\z)')
foreach ($taskBlock in $taskBlocks) {
    $taskId = $taskBlock.Groups['id'].Value
    $dependencyRows = [regex]::Matches($taskBlock.Value, '(?m)^\| \*\*8\. Dependencias previas\*\* \| (?<dependencies>.*?) \|$')
    if ($dependencyRows.Count -ne 1) {
        Add-Failure "$taskId must contain exactly one Dependencias previas field; found $($dependencyRows.Count)."
        $dependencyReferencesValid = $false
        $taskDependencies[$taskId] = @()
        continue
    }

    try {
        $dependencies = @(Get-HardTaskDependencies -DependencyText $dependencyRows[0].Groups['dependencies'].Value)
    }
    catch {
        Add-Failure "$taskId has an invalid dependency expression: $($_.Exception.Message)"
        $dependencyReferencesValid = $false
        $dependencies = @()
    }

    foreach ($dependency in $dependencies) {
        if (-not $planTaskIds.Contains($dependency)) {
            Add-Failure "$taskId references missing dependency $dependency."
            $dependencyReferencesValid = $false
        }
        if ($dependency -eq $taskId) {
            $selfDependencyCount++
            Add-Failure "$taskId contains a self-dependency."
        }
    }
    $taskDependencies[$taskId] = $dependencies
}

if ($taskBlocks.Count -ne $planTaskIds.Count) {
    Add-Failure "Dependency parser found $($taskBlocks.Count) task blocks for $($planTaskIds.Count) task IDs."
    $dependencyReferencesValid = $false
}

$indegree = @{}
$dependents = @{}
foreach ($taskId in $planTaskIds) {
    $indegree[$taskId] = 0
    $dependents[$taskId] = [System.Collections.Generic.List[string]]::new()
}
foreach ($taskId in $planTaskIds) {
    foreach ($dependency in @($taskDependencies[$taskId])) {
        if ($planTaskIds.Contains($dependency)) {
            $indegree[$taskId]++
            [void]$dependents[$dependency].Add($taskId)
        }
    }
}

$readyTasks = [System.Collections.Generic.SortedSet[string]]::new()
foreach ($taskId in $planTaskIds) {
    if ($indegree[$taskId] -eq 0) {
        [void]$readyTasks.Add($taskId)
    }
}
$topologicalOrder = [System.Collections.Generic.List[string]]::new()
while ($readyTasks.Count -gt 0) {
    $taskId = $readyTasks.Min
    [void]$readyTasks.Remove($taskId)
    [void]$topologicalOrder.Add($taskId)
    foreach ($dependent in @($dependents[$taskId] | Sort-Object)) {
        $indegree[$dependent]--
        if ($indegree[$dependent] -eq 0) {
            [void]$readyTasks.Add($dependent)
        }
    }
}

$dependencyCycleCount = 0
if ($topologicalOrder.Count -ne $planTaskIds.Count) {
    $dependencyCycleCount = 1
    $cyclePath = @(Find-DependencyCycle -Dependencies $taskDependencies)
    $cycleDescription = if ($cyclePath.Count -gt 0) { $cyclePath -join ' -> ' } else { 'cycle path unavailable' }
    Add-Failure "Plan task dependency cycle detected: $cycleDescription."
}

$requiredFields = @(
    "requirement_id", "category", "requirement_or_policy", "classification",
    "jurisdiction_or_source", "trigger", "data_or_document", "affected_module",
    "current_repo_state", "required_control", "required_backend_validation",
    "required_audit", "required_outbox_event", "required_retention_rule",
    "required_privacy_rule", "required_access_scope", "required_test",
    "required_evidence", "implementation_task", "gate", "owner",
    "external_validation_dependency", "pilot_blocker", "production_blocker", "notes"
)
$validClassifications = @(
    "APPROVED_EXTERNAL_REQUIREMENT", "APPROVED_BUSINESS_POLICY", "TECHNICAL_DERIVATION",
    "EXTERNAL_VALIDATION_REQUIRED", "IMPLEMENTATION_PENDING", "OUT_OF_SCOPE_EXPLICIT",
    "NOT_APPLICABLE", "UNKNOWN"
)
$validRepoStates = @(
    "IMPLEMENTED_AND_VERIFIED", "IMPLEMENTED_NOT_VERIFIED", "PARTIAL", "ABSENT",
    "EXTERNAL_DEPENDENCY", "BLOCKED_BY_DECISION", "IMPLEMENTATION_GAP"
)

Test-UniqueIds -Items $requirements -PropertyName "requirement_id" -Label "Requirement"
Test-UniqueIds -Items $tests -PropertyName "test_id" -Label "Test"
Test-UniqueIds -Items $externalValidations -PropertyName "validation_id" -Label "External validation"
Test-UniqueIds -Items $planGaps -PropertyName "gap_id" -Label "Plan gap"

if ($requirements.Count -ne 53) {
    Add-Failure "Expected 53 external requirements, found $($requirements.Count)."
}
if ($tests.Count -ne 53) {
    Add-Failure "Expected 53 requirement tests, found $($tests.Count)."
}
if ($externalValidations.Count -ne 6) {
    Add-Failure "Expected 6 external validations, found $($externalValidations.Count)."
}
if ($outOfScope.Count -ne 7) {
    Add-Failure "Expected 7 accepted out-of-scope items, found $($outOfScope.Count)."
}
if ($planGaps.Count -ne 0) {
    Add-Failure "Expected zero unresolved Plan gaps, found $($planGaps.Count)."
}

$requirementIdSet = [System.Collections.Generic.HashSet[string]]::new([string[]]($requirements | ForEach-Object requirement_id))
$testIdSet = [System.Collections.Generic.HashSet[string]]::new([string[]]($tests | ForEach-Object test_id))
$validationIdSet = [System.Collections.Generic.HashSet[string]]::new([string[]]($externalValidations | ForEach-Object validation_id))
$gapIdSet = [System.Collections.Generic.HashSet[string]]::new()
foreach ($gap in $planGaps) {
    [void]$gapIdSet.Add([string]$gap.gap_id)
}

foreach ($requirement in $requirements) {
    $id = [string]$requirement.requirement_id
    if ($id -notmatch '^EXT-[A-Z]+-\d{3}$') {
        Add-Failure "Invalid requirement ID format: $id."
    }

    foreach ($field in $requiredFields) {
        if (-not ($requirement.PSObject.Properties.Name -contains $field)) {
            Add-Failure "$id is missing field $field."
            continue
        }
        if ($field -notin @("external_validation_dependency", "pilot_blocker", "production_blocker") -and -not (Test-HasValue $requirement.$field)) {
            Add-Failure "$id has an empty required field $field."
        }
    }

    if ($requirement.classification -notin $validClassifications) {
        Add-Failure "$id has invalid classification $($requirement.classification)."
    }
    if ($requirement.current_repo_state -notin $validRepoStates) {
        Add-Failure "$id has invalid repository state $($requirement.current_repo_state)."
    }
    if ($requirement.classification -eq "UNKNOWN" -or $requirement.current_repo_state -eq "UNKNOWN") {
        Add-Failure "$id contains an untreated UNKNOWN state."
    }
    if ($requirement.pilot_blocker -isnot [bool] -or $requirement.production_blocker -isnot [bool]) {
        Add-Failure "$id blocker fields must be Boolean."
    }

    foreach ($taskReference in @($requirement.implementation_task)) {
        if ($taskReference -match '^ZM-FIN-\d{3}$') {
            if (-not $planTaskIds.Contains($taskReference)) {
                Add-Failure "$id references missing Plan task $taskReference."
            }
        }
        elseif ($taskReference -match '^PLAN_GAP:(.+)$') {
            if (-not $gapIdSet.Contains($Matches[1])) {
                Add-Failure "$id references missing Plan gap $($Matches[1])."
            }
        }
        else {
            Add-Failure "$id has invalid implementation task reference $taskReference."
        }
    }

    foreach ($gate in @($requirement.gate)) {
        if (-not $validGates.Contains($gate)) {
            Add-Failure "$id references invalid gate $gate."
        }
    }
    foreach ($testReference in @($requirement.required_test)) {
        if (-not $testIdSet.Contains($testReference)) {
            Add-Failure "$id references missing test $testReference."
        }
    }
    foreach ($validationReference in @($requirement.external_validation_dependency)) {
        if (-not $validationIdSet.Contains($validationReference)) {
            Add-Failure "$id references missing external validation $validationReference."
        }
    }
    foreach ($decisionMatch in [regex]::Matches([string]$requirement.jurisdiction_or_source, '\bDEC-\d{2}\b')) {
        if (-not $decisionIds.Contains($decisionMatch.Value)) {
            Add-Failure "$id references missing decision $($decisionMatch.Value)."
        }
    }
}

$validTestTypes = @("UNIT", "INTEGRATION", "CONTRACT", "E2E", "SECURITY", "PRIVACY", "RETENTION", "EXPORT", "RESTORE", "PROVIDER_VALIDATION", "UAT", "MANUAL_CONTROL")
foreach ($test in $tests) {
    $testId = [string]$test.test_id
    foreach ($field in @("test_id", "requirement_id", "test_type", "preconditions", "scenario", "expected", "evidence", "later_ZM_FIN")) {
        if (-not ($test.PSObject.Properties.Name -contains $field) -or -not (Test-HasValue $test.$field)) {
            Add-Failure "$testId is missing or has empty field $field."
        }
    }
    if ($testId -notmatch '^TST-[A-Z]+-\d{3}$') {
        Add-Failure "Invalid test ID format: $testId."
    }
    if (-not $requirementIdSet.Contains([string]$test.requirement_id)) {
        Add-Failure "$testId references missing requirement $($test.requirement_id)."
    }
    if ($test.test_type -notin $validTestTypes) {
        Add-Failure "$testId has invalid type $($test.test_type)."
    }
    foreach ($taskReference in @($test.later_ZM_FIN)) {
        if ($taskReference -match '^ZM-FIN-\d{3}$') {
            if (-not $planTaskIds.Contains($taskReference)) {
                Add-Failure "$testId references missing Plan task $taskReference."
            }
        }
        elseif ($taskReference -match '^PLAN_GAP:(.+)$') {
            if (-not $gapIdSet.Contains($Matches[1])) {
                Add-Failure "$testId references missing Plan gap $($Matches[1])."
            }
        }
        else {
            Add-Failure "$testId has invalid later task reference $taskReference."
        }
    }
}

foreach ($validation in $externalValidations) {
    if (-not (Test-HasValue $validation.status) -or $validation.status -match '^UNKNOWN$') {
        Add-Failure "$($validation.validation_id) has no explicit status."
    }
    foreach ($requirementReference in @($validation.requirement_ids)) {
        if (-not $requirementIdSet.Contains($requirementReference)) {
            Add-Failure "$($validation.validation_id) references missing requirement $requirementReference."
        }
    }
    foreach ($gate in @($validation.gate)) {
        if (-not $validGates.Contains($gate)) {
            Add-Failure "$($validation.validation_id) references invalid gate $gate."
        }
    }
}

$outOfScopeIdSet = [System.Collections.Generic.HashSet[string]]::new([string[]]($outOfScope | ForEach-Object requirement_id))
foreach ($item in $outOfScope) {
    foreach ($field in @("requirement_id", "reason_out_of_scope", "risk", "owner_acceptance", "future_trigger", "future_task_or_gate")) {
        if (-not ($item.PSObject.Properties.Name -contains $field) -or -not (Test-HasValue $item.$field)) {
            Add-Failure "Out-of-scope item $($item.requirement_id) is missing or has empty field $field."
        }
    }
    if (-not $requirementIdSet.Contains([string]$item.requirement_id)) {
        Add-Failure "Out-of-scope item references missing requirement $($item.requirement_id)."
    }
    if ([string]$item.owner_acceptance -notmatch '(?i)approved') {
        Add-Failure "Out-of-scope item $($item.requirement_id) lacks explicit approved owner acceptance."
    }
}
foreach ($requirement in @($requirements | Where-Object classification -eq "OUT_OF_SCOPE_EXPLICIT")) {
    if (-not $outOfScopeIdSet.Contains([string]$requirement.requirement_id)) {
        Add-Failure "$($requirement.requirement_id) is out of scope but has no acceptance record."
    }
}

foreach ($gap in $planGaps) {
    foreach ($field in @("gap_id", "requirement_ids", "missing_capability", "why_existing_tasks_insufficient", "proposed_location")) {
        if (-not ($gap.PSObject.Properties.Name -contains $field) -or -not (Test-HasValue $gap.$field)) {
            Add-Failure "Plan gap $($gap.gap_id) is missing or has empty field $field."
        }
    }
    foreach ($requirementReference in @($gap.requirement_ids)) {
        if (-not $requirementIdSet.Contains($requirementReference)) {
            Add-Failure "$($gap.gap_id) references missing requirement $requirementReference."
        }
    }
}

$untestedRequirements = @($requirements | Where-Object { @($_.required_test | Where-Object { $testIdSet.Contains($_) }).Count -eq 0 })
if ($untestedRequirements.Count -gt 0) {
    Add-Failure "Requirements without a valid test: $($untestedRequirements.requirement_id -join ', ')."
}

$ownerDecisionsRequired = @($requirements | Where-Object { $_.current_repo_state -eq "BLOCKED_BY_DECISION" })
$unsupportedLegalClaims = @($requirements | Where-Object {
    $_.classification -eq "EXTERNAL_VALIDATION_REQUIRED" -and
    @($_.external_validation_dependency).Count -eq 0
})
if ($ownerDecisionsRequired.Count -gt 0) {
    Add-Failure "Owner decisions remain required for: $($ownerDecisionsRequired.requirement_id -join ', ')."
}
if ($unsupportedLegalClaims.Count -gt 0) {
    Add-Failure "External-validation requirements lack evidence gates: $($unsupportedLegalClaims.requirement_id -join ', ')."
}

$requiredInventoryTokens = @("Identity and personnel", "Customer orders", "Suppliers and purchases", "Sales and tickets", "Audit", "Outbox", "Logs", "Reports and exports", "Backups", "Fiscal records", "Privacy and ARCO")
foreach ($token in $requiredInventoryTokens) {
    if (-not $document.Contains($token)) {
        Add-Failure "Data inventory is missing $token."
    }
}

$requiredRetentionTokens = @("Sales/financial ledger", "Cash", "Orders", "Payments/refunds", "Inventory", "Production", "Audit", "Outbox", "Customer operational PII", "Employee data", "Supplier data", "Fiscal documents", "Logs", "Alerts/incidents", "Analytics facts", "Backups", "Exports")
foreach ($token in $requiredRetentionTokens) {
    if (-not $document.Contains("| $token |")) {
        Add-Failure "Retention inventory is missing category $token."
    }
}

if ($failures.Count -gt 0) {
    Write-Host "External requirements validation FAILED ($($failures.Count) issue(s)):" -ForegroundColor Red
    foreach ($failure in $failures) {
        Write-Host "- $failure" -ForegroundColor Red
    }
    exit 1
}

$categoryCounts = $requirements | Group-Object { ($_.requirement_id -split '-')[1] } | Sort-Object Name
Write-Host "External requirements validation PASS"
Write-Host "requirements=$($requirements.Count)"
Write-Host "tests=$($tests.Count)"
Write-Host "external_validations=$($externalValidations.Count)"
Write-Host "out_of_scope=$($outOfScope.Count)"
Write-Host "plan_gaps=$($planGaps.Count)"
Write-Host "plan_tasks=$($planTaskIds.Count)"
Write-Host "plan_task_ids_unique=$($planTaskIdList.Count -eq $planTaskIds.Count)"
Write-Host "dependency_references_valid=$dependencyReferencesValid"
Write-Host "self_dependency_count=$selfDependencyCount"
Write-Host "dependency_cycle_count=$dependencyCycleCount"
Write-Host "topological_task_count=$($topologicalOrder.Count)"
Write-Host "decisions=$($decisionIds.Count)"
Write-Host "existing_tasks_001_126_preserved=$(@($expectedPlanTaskIds[0..125] | Where-Object { -not $planTaskIds.Contains($_) }).Count -eq 0)"
Write-Host "new_tasks_127_130_present=$(@($expectedPlanTaskIds[126..129] | Where-Object { -not $planTaskIds.Contains($_) }).Count -eq 0)"
Write-Host "owner_decisions_required=$($ownerDecisionsRequired.Count)"
Write-Host "unsupported_legal_claims=$($unsupportedLegalClaims.Count)"
Write-Host "untreated_unknown=0"
foreach ($group in $categoryCounts) {
    Write-Host "category_$($group.Name)=$($group.Count)"
}
