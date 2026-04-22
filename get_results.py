import subprocess
import os
import re
import json
import csv
import time

script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(script_dir, ".."))

executable = os.path.join(repo_root, "heuristic")
COUNT_EXEC = 10

base_folder = os.path.join(repo_root, "instances_enic")
subfolders = [f"enic{year}" for year in range(14, 19)]  # enic14 até enic18
#subfolders = ["enic14"]
csv_output = os.path.join(script_dir, "resultados.csv")
results_base_folder = os.path.join(script_dir, "results")

# Criar pasta base de resultados, se necessário
os.makedirs(results_base_folder, exist_ok=True)

# Abrir CSV para salvar os resultados
with open(csv_output, mode="w", newline='') as csvfile:
    fieldnames = [
        "folder", "instance", "dictionary", "num_papers",
        "mean_saltos", "mean_extras", "mean_sessoes"
    ]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for subfolder in subfolders:
        instance_folder = os.path.join(base_folder, subfolder)
        print(f"\n=== Procurando em: {instance_folder} ===")

        instance_files = sorted([f for f in os.listdir(instance_folder) if f.startswith("instance_")])
        print(instance_files)
        for instance in instance_files:
            #if instance != 'instance_campusCCHSA_dia8.txt':
            #    continue
            #print(instance)
            dictionary = instance.replace("instance_", "dictionary_")
            instance_path = os.path.join(instance_folder, instance)
            dictionary_path = os.path.join(instance_folder, dictionary)

            if not os.path.exists(dictionary_path):
                print(f"Dictionary não encontrado: {dictionary_path}, pulando...")
                continue

            # Criar diretório para armazenar os resultados da instância
            instance_result_folder = os.path.join(results_base_folder, subfolder, instance.replace(".txt", ""))
            os.makedirs(instance_result_folder, exist_ok=True)

            # Abrir arquivo de log para essa instância
            log_path = os.path.join(instance_result_folder, "log.txt")
            with open(log_path, "w", buffering=1) as log_file:
                log_file.write(f"=== Rodando para {instance_path} e {dictionary_path} ===\n")
                log_file.flush()

                saltos = []
                extras = []
                sessoes = []
                num_papers = None  # vamos capturar na primeira execução

                for i in range(COUNT_EXEC):
                    log_file.write(f"\nExecução #{i+1}...\n")
                    log_file.flush()
                    
                    tentativa = 0
                    while True:
                        tentativa += 1
                        log_file.write(f"  Tentativa {tentativa}...\n")
                        log_file.flush()

                        try:
                            output_json_path = os.path.join(instance_result_folder, f"output_{i}.json")
                            
                            # Limpar o arquivo JSON antes de rodar, para garantir que não usemos lixo de uma execução falha
                            if os.path.exists(output_json_path):
                                os.remove(output_json_path)

                            # 1. Rodar o executável
                            result = subprocess.run(
                                [executable, instance_path, output_json_path, dictionary_path],
                                capture_output=True,
                                text=True,
                                timeout=300
                            )

                            output = result.stdout
                            log_file.write(output + "\n")
                            log_file.flush()

                            # 2. Verificar o código de retorno
                            if result.returncode != 0:
                                log_file.write(f"Erro: O processo falhou com código de retorno: {result.returncode}\n")
                                log_file.flush()
                                time.sleep(1)
                                continue

                            # 3. Tentar carregar o JSON e verificar se está vazio/inválido
                            with open(output_json_path, 'r') as result_file:
                                data_result = json.load(result_file)
                                
                            # Se o JSON carregar com sucesso, a execução é considerada válida
                            saltos.append(data_result.get('numSaltos', 0))
                            extras.append(data_result.get('numExtraProfs', 0))
                            sessoes.append(data_result.get('numUsedSessions', 0))
                            log_file.write(f"Sucesso. Saltos: {saltos[-1]}, Extras: {extras[-1]}, Sessoes: {sessoes[-1]}\n")
                            log_file.flush()
                            
                            # Capturar num_papers apenas na primeira execução bem-sucedida
                            if num_papers is None:
                                match = re.search(r'Papers:\s*(\d+)', output)
                                if match:
                                    num_papers = int(match.group(1))
                                    log_file.write(f"Número de papers: {num_papers}\n")
                                    log_file.flush()

                            break

                        except subprocess.TimeoutExpired:
                            log_file.write("Erro: O processo excedeu o tempo limite de execução (300s).\n")
                            log_file.flush()
                            time.sleep(1)
                        except FileNotFoundError:
                            log_file.write(f"Erro: O arquivo de saída JSON não foi criado/encontrado: {output_json_path}\n")
                            log_file.flush()
                            time.sleep(1)
                        except json.JSONDecodeError:
                            log_file.write(f"Erro: O arquivo JSON está vazio ou inválido: {output_json_path}\n")
                            log_file.flush()
                            time.sleep(1)
                        except Exception as e:
                            log_file.write(f"Erro inesperado durante a execução/leitura do JSON: {e}\n")
                            log_file.flush()
                            time.sleep(1)

                # Calcular médias
                mean_saltos = sum(saltos) / len(saltos) if saltos else 0
                mean_extras = sum(extras) / len(extras) if extras else 0
                mean_sessoes = sum(sessoes) / len(sessoes) if sessoes else 0

                log_file.write("\n=== Resultado médio ===\n")
                log_file.write(f"Salto médio: {mean_saltos}\n")
                log_file.write(f"Extra médio: {mean_extras}\n")
                log_file.write(f"Sessões médias: {mean_sessoes}\n")
                log_file.write(f"Número de papers: {num_papers}\n")
                log_file.flush()

            # Escrever no CSV
            writer.writerow({
                "folder": subfolder,
                "instance": instance,
                "dictionary": dictionary,
                "num_papers": num_papers or 0,
                "mean_saltos": mean_saltos,
                "mean_extras": mean_extras,
                "mean_sessoes": mean_sessoes
            })