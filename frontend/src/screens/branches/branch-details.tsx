import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import getBranchDetails from "../../graphql/queries/branches/getBranchDetails";
import LoadingScreen from "../loading-screen/loading-screen";
import { formatDistanceToNow } from "date-fns";
import { Pill } from "../../components/pill";
import { Badge } from "../../components/badge";
import { ALERT_TYPES, Alert } from "../../components/alert";
import { toast } from "react-toastify";
import { BUTTON_TYPES, Button } from "../../components/button";
import { CheckIcon, ShieldCheckIcon } from "@heroicons/react/20/solid";
import rebaseBranch from "../../graphql/mutations/branches/rebaseBranch";
import validateBranch from "../../graphql/mutations/branches/validateBranch";
import deleteBranch from "../../graphql/mutations/branches/deleteBranch";
import { constructPath } from "../../utils/fetch";
import mergeBranch from "../../graphql/mutations/branches/mergeBranch";
import { ArrowPathIcon, TrashIcon } from "@heroicons/react/24/outline";
import ModalDelete from "../../components/modal-delete";

export const BranchDetails = () => {
  const { branchname } = useParams();

  const [branch, setBranch] = useState({} as any);
  const [isLoadingBranch, setIsLoadingBranch] = useState(true);
  const [isLoadingRequest, setIsLoadingRequest] = useState(false);
  const [displayModal, setDisplayModal] = useState(false);
  const [detailsContent, setDetailsContent] = useState({});

  const navigate = useNavigate();

  const fetchBranchDetails = useCallback(
    async () => {
      if (!branchname) return;

      try {
        const branchDetails = await getBranchDetails(branchname);

        if (!branchDetails?.name) {
          navigate("/branches");
        }

        setBranch(branchDetails);
        setIsLoadingBranch(false);
      } catch(err) {
        console.error("err: ", err);
        setIsLoadingBranch(false);
      }
    }, [branchname, navigate]
  );

  useEffect(
    () => {
      fetchBranchDetails();
    },
    [fetchBranchDetails]
  );

  const branchAction = async ({
    successMessage,
    errorMessage,
    request,
    options
  }: any) => {
    if (!branchname) return;

    try {
      setIsLoadingRequest(true);
      const result = await request(options);
      setDetailsContent(result);

      toast(<Alert type={ALERT_TYPES.SUCCESS} message={successMessage} />);
    } catch (error: any) {
      console.log("error: ", error);
      setDetailsContent(error);

      toast(<Alert type={ALERT_TYPES.SUCCESS} message={errorMessage} />);
    }

    setIsLoadingRequest(false);
  };

  return (
    <div className="bg-white p-6">
      {
        isLoadingBranch
        && <LoadingScreen />
      }

      {
        displayModal
        && (
          <ModalDelete
            title="Delete"
            description={
              (
                <>
                  Are you sure you want to remove the the branch:<br/> <b>`{branch?.name}`</b>?
                </>
              )
            }
            onCancel={() => setDisplayModal(false)}
            onDelete={
              async () => {
                await branchAction({
                  successMessage: "Branch deleted successfuly!",
                  errorMessage: "An error occured while deleting the branch",
                  request: deleteBranch,
                  options: {
                    name: branch.name
                  }
                });

                navigate(constructPath("/branches"));

                window.location.reload();
              }
            }
            open={!!displayModal}
            setOpen={() => setDisplayModal(false)}
          />
        )
      }

      {
        !isLoadingBranch
        && branch?.name
        && (
          <>
            <div className="border-t border-b border-gray-200 px-2 py-2 sm:p-0 mb-6">
              <dl className="divide-y divide-gray-200">
                <div className="py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-5 sm:px-6">
                  <dt className="text-sm font-medium text-gray-500">Name</dt>
                  <dd className="flex mt-1 text-sm text-gray-900 sm:col-span-2 sm:mt-0">{branch.name}</dd>
                </div>
                <div className="py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-5 sm:px-6">
                  <dt className="text-sm font-medium text-gray-500">Origin branch</dt>
                  <dd className="flex mt-1 text-sm text-gray-900 sm:col-span-2 sm:mt-0"><Badge>{branch.origin_branch}</Badge></dd>
                </div>
                <div className="py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-5 sm:px-6">
                  <dt className="text-sm font-medium text-gray-500">Branched</dt>
                  <dd className="flex mt-1 text-sm text-gray-900 sm:col-span-2 sm:mt-0"> <Pill>{formatDistanceToNow(new Date(branch.branched_from), { addSuffix: true })}</Pill></dd>
                </div>
                <div className="py-2 sm:grid sm:grid-cols-3 sm:gap-4 sm:py-5 sm:px-6">
                  <dt className="text-sm font-medium text-gray-500">Created</dt>
                  <dd className="flex mt-1 text-sm text-gray-900 sm:col-span-2 sm:mt-0"> <Pill>{formatDistanceToNow(new Date(branch.created_at), { addSuffix: true })}</Pill></dd>
                </div>
              </dl>
            </div>

          </>
        )
      }

      <div className="">
        <div className="mb-6">
          {
            branch?.name
            && (
              <>
                <div className="flex flex-1 flex-col md:flex-row">
                  <Button
                    className="mr-0 md:mr-3"
                    onClick={() => branchAction({
                      successMessage: "Branch merged successfuly!",
                      errorMessage: "An error occured while merging the branch",
                      request: mergeBranch,
                      options: {
                        name: branch.name
                      }
                    })}
                    buttonType={BUTTON_TYPES.VALIDATE}
                    disabled={branch.is_default}
                  >
                    Merge
                    <CheckIcon className="-mr-0.5 h-4 w-4" aria-hidden="true" />
                  </Button>

                  <Button
                    className="mr-0 md:mr-3"
                    onClick={() => branchAction({
                      successMessage: "Branch rebased successfuly!",
                      errorMessage: "An error occured while rebasing the branch",
                      request: rebaseBranch,
                      options: {
                        name: branch.name
                      }
                    })}
                    disabled={branch.is_default}
                  >
                    Rebase
                    <ArrowPathIcon className="-mr-0.5 h-4 w-4" aria-hidden="true" />
                  </Button>

                  <Button
                    className="mr-0 md:mr-3"
                    onClick={() => branchAction({
                      successMessage: "The branch is valid!",
                      errorMessage: "An error occured while validating the branch",
                      request: validateBranch,
                      options: {
                        name: branch.name
                      }
                    })}
                    buttonType={BUTTON_TYPES.WARNING}
                    disabled={branch.is_default}
                  >
                    Validate
                    <ShieldCheckIcon className="-mr-0.5 h-4 w-4" aria-hidden="true" />
                  </Button>

                  <Button
                    className="mr-0 md:mr-3"
                    onClick={
                      () => setDisplayModal(true)
                    }
                    buttonType={BUTTON_TYPES.CANCEL}
                    disabled={branch.is_default}
                  >
                    Delete
                    <TrashIcon className="-mr-0.5 h-4 w-4" aria-hidden="true" />
                  </Button>
                </div>
              </>
            )
          }
        </div>

        {
          isLoadingRequest
          && (
            <div className="">
              <LoadingScreen />
            </div>
          )
        }

        {
          detailsContent
          && !isLoadingRequest
          && (
            <div className="">
              <pre>
                {JSON.stringify(detailsContent, null, 2)}
              </pre>
            </div>
          )
        }
      </div>
    </div>
  );
};