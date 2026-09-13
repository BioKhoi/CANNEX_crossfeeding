#!/usr/bin/env Rscript

arguments <- commandArgs(trailingOnly = FALSE)
file_argument <- grep("^--file=", arguments, value = TRUE)

if (length(file_argument) != 1L) {
  stop("Could not determine the location of render_visualizations.R.")
}

script_path <- sub("^--file=", "", file_argument)
visualization_directory <- dirname(normalizePath(
  script_path, winslash = "/", mustWork = TRUE
))

if (!requireNamespace("rmarkdown", quietly = TRUE)) {
  stop(
    "The R package 'rmarkdown' is required. Install it with ",
    "install.packages('rmarkdown')."
  )
}

input_file <- file.path(
  visualization_directory, "reproduce_manuscript_visualizations.Rmd"
)
output_directory <- file.path(visualization_directory, "outputs")
dir.create(output_directory, recursive = TRUE, showWarnings = FALSE)

rmarkdown::render(
  input = input_file,
  output_file = "CANNEX_manuscript_visualizations.html",
  output_dir = output_directory,
  envir = new.env(parent = globalenv()),
  quiet = FALSE
)

message(
  "Rendered: ",
  file.path(output_directory, "CANNEX_manuscript_visualizations.html")
)
