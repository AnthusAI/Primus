{{/*
Expand the name of the chart.
*/}}
{{- define "primus-worker.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create the name of the object-store credential Secret.
*/}}
{{- define "primus-worker.objectStoreSecretName" -}}
{{- required "objectStore.existingSecret is required when objectStore.enabled=true" .Values.objectStore.existingSecret -}}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "primus-worker.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "primus-worker.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "primus-worker.labels" -}}
helm.sh/chart: {{ include "primus-worker.chart" . }}
{{ include "primus-worker.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "primus-worker.selectorLabels" -}}
app.kubernetes.io/name: {{ include "primus-worker.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: worker
{{- end }}

{{/*
Pod labels
*/}}
{{- define "primus-worker.podLabels" -}}
{{ include "primus-worker.selectorLabels" . }}
worker-type: {{ .Values.workerType }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "primus-worker.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "primus-worker.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the secret to use for Primus API
*/}}
{{- define "primus-worker.secretName" -}}
{{- if .Values.primus.existingSecret }}
{{- .Values.primus.existingSecret }}
{{- else }}
{{- include "primus-worker.fullname" . }}-secrets
{{- end }}
{{- end }}

{{/*
Create the Primus API URL for the worker secret.
*/}}
{{- define "primus-worker.apiUrl" -}}
{{- if .Values.primus.api.url -}}
{{- .Values.primus.api.url -}}
{{- else -}}
{{- $global := default dict .Values.global -}}
{{- $services := default dict $global.services -}}
{{- $graphqlProxy := default dict $services.graphqlProxy -}}
{{- if $graphqlProxy.externalUrl -}}
{{- $graphqlProxy.externalUrl -}}
{{- else if and $graphqlProxy.host $graphqlProxy.port -}}
{{- $host := tpl $graphqlProxy.host . -}}
{{- $port := $graphqlProxy.port -}}
{{- $path := default "/graphql" $graphqlProxy.path -}}
{{- printf "http://%s:%d%s" $host (int $port) $path -}}
{{- else -}}
{{- "" -}}
{{- end -}}
{{- end -}}
{{- end }}

{{/*
Create the name of the secret to use for AWS credentials
*/}}
{{- define "primus-worker.awsSecretName" -}}
{{- if .Values.scoreProcessor.aws.existingSecret }}
{{- .Values.scoreProcessor.aws.existingSecret }}
{{- else }}
{{- include "primus-worker.fullname" . }}-aws-secrets
{{- end }}
{{- end }}

{{/*
Create the name of the secret to use for Celery broker
*/}}
{{- define "primus-worker.celerySecretName" -}}
{{- if .Values.celery.broker.existingSecret }}
{{- .Values.celery.broker.existingSecret }}
{{- else }}
{{- include "primus-worker.fullname" . }}-celery-secrets
{{- end }}
{{- end }}

{{/*
Create the Gateway name for scoring API HTTP routing.
*/}}
{{- define "primus-worker.gatewayName" -}}
{{- if .Values.scoringApi.gateway.gatewayName }}
{{- .Values.scoringApi.gateway.gatewayName | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-gateway" (include "primus-worker.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Create the HTTPRoute name for scoring API HTTP routing.
*/}}
{{- define "primus-worker.routeName" -}}
{{- if .Values.scoringApi.gateway.routeName }}
{{- .Values.scoringApi.gateway.routeName | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-route" (include "primus-worker.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
