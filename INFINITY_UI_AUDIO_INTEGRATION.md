# ∞ — UI / Audio Engine Integration Contract

Статус: технический контракт для реализации в Windows-клиенте. Это не утверждение, что мост уже реализован.

## Архитектура

UI не генерирует звук сам и не хранит отдельную копию музыкального состояния. UI отправляет команды в единый Application Controller. Контроллер валидирует команды, обновляет Project State и передаёт realtime-команды в Audio Engine. Движок сообщает UI событиями о состоянии транспорта, голосах, уровнях, клиппинге и ошибках.

Слои:
1. UI — пэды, секвенсор, браузер, микшер, сцены и редакторы.
2. Application Controller — команды, Undo/Redo, проект, сохранение, маршрутизация событий.
3. Project State — 8 дорожек, 12 pad assignments, 64 steps, clips/groups, scenes A-D, automation, parameter locks.
4. Audio Engine — sample voices, synth voices, sequencer clock, mixer, effects, recording, resampling, export.
5. Device I/O — ASIO/WASAPI, MIDI input/output, sample-rate/buffer configuration.

## Командный интерфейс

Все команды должны иметь устойчивые идентификаторы и валидируемые аргументы:
- transport.play, transport.stop, transport.record, transport.set_tempo
- pad.trigger, pad.release, pad.assign_sample
- track.set_mute, track.set_solo, track.set_gain, track.set_pan
- step.set_enabled, step.set_velocity, step.set_probability, step.set_condition
- parameter.set, parameter.lock, automation.write
- scene.launch, clip.launch, group.launch
- sample.load, sample.preview, sample.stop_preview
- record.start, record.stop, resample.start, export.render

Команды UI не должны напрямую вызывать тяжёлые DSP-операции из UI-потока.

## События движка для UI

- transport.position — такт, доля, шаг и playhead.
- pad.voice_started / pad.voice_finished — активная подсветка пэда.
- track.meter — peak/RMS и состояние clip.
- master.meter — peak/RMS/true peak и clip warning.
- audio.device_changed — устройство, sample rate, buffer size.
- audio.xruns — счётчик underruns.
- project.dirty_changed — признак несохранённых изменений.
- record.state_changed — состояние записи.
- export.progress / export.completed / export.failed.
- engine.error — диагностируемая ошибка с понятным пользовательским сообщением.

События аудио-потока должны передаваться через lock-free или bounded queue; UI читает агрегированные данные с безопасной частотой. Никакие блокирующие файловые операции, выделения памяти или mutex ожидания не допускаются в аудио callback.

## Единая модель проекта

- 8 tracks, каждая содержит sample/synth source, gain, pan, mute/solo, inserts и send levels.
- 12 pads назначаются на источники/слоты, не должны быть отдельными демо-кнопками.
- 64 steps на дорожку; шаг хранит enabled, velocity, microtiming, probability/condition и parameter locks.
- Scenes A-D хранят ссылки/снимки паттернов и параметров с квантованным запуском.
- Автоматизация и locks должны управлять теми же параметрами, которые доступны в SOUND/MIX/FX.
- Undo/Redo изменяет Project State и посылает согласованные команды движку.

## Сохранение и экспорт

Проект хранит версию схемы, относительные пути к аудио, настройки устройства не как обязательную зависимость, темп, swing, дорожки, паттерны, сцены, automation, locks и FX. Отсутствующие семплы показываются как missing media с возможностью relink.

Экспорт рендерит тот же граф маршрутизации и эффектов, что слышен при playback. Поддержка WAV и FLAC; формат, частота, bit depth и normalization задаются явно. Offline render не должен зависеть от размера UI окна.

## Критерии интеграции

1. Нажатие пэда вызывает реальный sample/synth voice через Audio Engine.
2. Шаг секвенсора запускает тот же voice через аудиочасы движка, не через UI timer.
3. Мьют, соло, громкость, панорама и эффекты слышимо меняют соответствующий канал.
4. Playhead, пэды и meters отражают фактическое состояние движка, а не декоративную анимацию.
5. Сцена A/B/C/D переключается квантованно без остановки транспорта.
6. Save/reopen сохраняет музыкальное состояние; Undo/Redo откатывает музыкальные действия.
7. Запись и экспорт содержат фактический сигнал master bus.
8. Потеря аудиоустройства и underruns отображаются понятным статусом, приложение не зависает.

## Правило готовности

Функция считается готовой только после теста через пользовательский интерфейс и проверку аудиосигнала. Наличие кнопки, класса или успешной компиляции само по себе не является готовой функцией.