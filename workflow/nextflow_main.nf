// Skeleton Nextflow pipeline mirroring the OpenEBench 3-step container pattern
// (validation -> metrics generation -> consolidation), following the structure
// used by https://github.com/inab/TCGA_benchmarking_workflow

nextflow.enable.dsl=2

params.predictionsFile   = null   // participant predictions.csv (entry_id,raw_score)
params.public_ref_dir    = "datasets/public_reference"
params.participant_name  = null
params.metrics_ref_dir   = "datasets/metrics_reference"
params.threshold         = null
params.community_id      = "OEBC_3DBioinfo"
params.challenge_id      = "3DBioinfo:PPI-PhysioClassification"
params.assess_dir        = "assessment_out"
params.results_dir       = "results"

process VALIDATE {
    input:
      path predictions
      path public_ref_dir
    output:
      path "validation_out/validation_result.json"
    script:
    """
    mkdir -p validation_out
    python3 ${baseDir}/workflow/validate.py \
        --input ${predictions} --public_ref_dir ${public_ref_dir} \
        --community_id ${params.community_id} --challenges_ids ${params.challenge_id} \
        --participant_id ${params.participant_name} --outdir validation_out
    """
}

process COMPUTE_METRICS {
    input:
      path predictions
      path goldstandard_dir
    output:
      path "assessment_out/assessment_results.json"
    script:
    def thrArg = params.threshold ? "--threshold ${params.threshold}" : ""
    """
    mkdir -p assessment_out
    python3 ${baseDir}/workflow/compute_metrics.py \
        --input ${predictions} --goldstandard_dir ${goldstandard_dir} \
        --community_id ${params.community_id} --challenges_ids ${params.challenge_id} \
        --participant_id ${params.participant_name} ${thrArg} --outdir assessment_out
    """
}

process CONSOLIDATE {
    publishDir params.results_dir, mode: "copy"
    input:
      path assess_dir
    output:
      path "consolidated/data_model_export.json"
      path "consolidated/leaderboard.svg", optional: true
    script:
    """
    python3 ${baseDir}/workflow/consolidate.py \
        --assess_dir ${assess_dir} --community_id ${params.community_id} \
        --challenge_id ${params.challenge_id} --outdir consolidated
    """
}

workflow {
    predictions_ch = Channel.fromPath(params.predictionsFile)
    public_ref_ch  = Channel.fromPath(params.public_ref_dir)
    gold_ch        = Channel.fromPath(params.metrics_ref_dir)

    VALIDATE(predictions_ch, public_ref_ch)
    COMPUTE_METRICS(predictions_ch, gold_ch)
    // In a real multi-participant run, COMPUTE_METRICS output for every
    // participant is collected into params.assess_dir before CONSOLIDATE runs.
}
