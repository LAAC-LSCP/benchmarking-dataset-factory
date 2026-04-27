.PHONY: get_annotations drop_annotations

get_annotations:
	datalad get -n datasets/* -J 5;
	datalad get datasets/*/annotations/*eaf*/*/converted/** -J 5;
	datalad get datasets/*/annotations/*eaf*/converted/** -J 5;
	datalad get datasets/*/annotations/*cha*/*/converted/** -J 5;
	datalad get datasets/*/annotations/*cha*/converted/** -J 5;
	datalad get datasets/*/annotations/*textgrid*/*/converted/** -J 5;
	datalad get datasets/*/annotations/*solis*/*/converted/** -J 5;
	datalad get datasets/*/annotations/**/*.yml -J 5;

drop_annotations:
	datalad drop datasets/**;